"""
LLM Mapping Generator Module

This module handles the integration with Databricks API to generate field mappings
using AI analysis of source data and target stage fields.
"""

import json
import openai
import requests
from typing import List, Dict, Any, Optional


class LLMMapperConfig:
    """Configuration class for LLM mapping generation (Databricks only)."""
    def __init__(self, token: str = None):
        self.base_url = "https://dbc-3735add4-1cb6.cloud.databricks.com/serving-endpoints"
        self.model = "databricks-claude-sonnet-4"
        self.token = token
        self.timeout = 600  # 5 minutes timeout for LLM processing
        self.temperature = 0.1
        self.max_tokens = 2000


class LLMMapper:
    """Main class for generating field mappings using LLM."""
    
    def __init__(self, config: Optional[LLMMapperConfig] = None):
        self.config = config or LLMMapperConfig()
        
        # Available transformation functions
        self.transformation_functions = {
            'Upper': 'Convert to uppercase',
            'Lower': 'Convert to lowercase',
            'Trim': 'Remove leading/trailing spaces',
            'Title': 'Convert to title case',
            'Substring': 'Extract substring',
            'Replace': 'Replace text',
            'Concatenate': 'Combine fields',
            'Left': 'Get leftmost n characters',
            'Right': 'Get rightmost n characters',
            'DateFormat': 'Format dates',
            'IsNull': 'Check for null values',
            'NotNull': 'Check for non-null values',
            'Length': 'Get field length',
            'Contains': 'Check if contains substring'
        }
    
    def generate_mappings(self, source_headers: List[str], source_data_sample: List[List[str]], 
                         stage_fields: List[str]) -> Dict[str, Any]:
        """
        Generate field mappings using LLM analysis via Databricks API.
        Args:
            source_headers: List of source file column headers
            source_data_sample: Sample rows from source data (top 10 rows)
            stage_fields: List of target stage field names
        Returns:
            Dictionary containing success status, mappings, and reasoning
        """
        try:
            # Create the prompt for the LLM
            prompt = self._create_mapping_prompt(source_headers, source_data_sample, stage_fields)
            # Call Databricks API
            api_response = self._call_databricks_api(prompt)
            # Parse the response to extract mappings
            mappings = self._parse_llm_response(api_response)
            # Extract reasoning if available
            reasoning = self._extract_reasoning(api_response)
            return {
                'success': True,
                'mappings': mappings,
                'reasoning': reasoning,
                'raw_response': api_response.get('choices', [{}])[0].get('message', {}).get('content', '')
            }
        except openai.OpenAIError as e:
            # Handle OpenAI/Databricks API errors
            error_message = str(e)
            if '403' in error_message or 'blocked by Databricks IP ACL' in error_message:
                return {
                    'success': False,
                    'error': 'Access denied: Your IP address is blocked by Databricks IP ACL. Please contact your Databricks admin to allow your IP or use an allowed network.',
                    'mappings': {},
                    'reasoning': ''
                }
            return {
                'success': False,
                'error': f'Databricks API error: {error_message}',
                'mappings': {},
                'reasoning': ''
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"LLM mapping generation failed: {str(e)}",
                'mappings': {},
                'reasoning': ''
            }
    
    def _create_mapping_prompt(self, source_headers: List[str], source_data_sample: List[List[str]], 
                              stage_fields: List[str]) -> str:
        """Create a detailed prompt for the LLM to generate field mappings."""
        
        # Format source data sample for better readability
        sample_data_text = self._format_sample_data(source_headers, source_data_sample)
        
        # Create function documentation
        functions_doc = self._create_functions_documentation()
        
        prompt = f"""
You are a data mapping expert specializing in healthcare eligibility data transformation. 
I need you to analyze source data and create precise field mappings to target stage fields.

SOURCE DATA STRUCTURE:
Headers: {', '.join(source_headers)}

SAMPLE DATA (showing patterns and data types):
{sample_data_text}

TARGET STAGE FIELDS (Eligibility Domain):
{', '.join(stage_fields)}

{functions_doc}

MAPPING REQUIREMENTS:
1. Analyze field names for semantic similarity (e.g., FirstName -> memberFirst)
2. Consider data types and formats 
3. Apply appropriate transformations for data quality:
   - Use Trim() to remove whitespace
   - Use Upper() for standardized text fields
   - Use proper date formatting for date fields
   - Use Concatenate() when combining fields makes sense
4. Only create mappings where there's clear correspondence
5. Prioritize data quality and standardization

RESPONSE FORMAT:
Respond with a JSON object containing:
{{
    "mappings": {{
        "memberFirst": "Upper(Trim(FirstName))",
        "memberLast": "Upper(Trim(LastName))",
        "mbrDOB": "DOB",
        "memberID": "MemberID"
    }},
    "reasoning": "Brief explanation of mapping logic and decisions made"
}}

Important: Only include mappings where you can confidently match source fields to stage fields based on semantic meaning and data compatibility.
"""
        
        return prompt
    
    def _format_sample_data(self, headers: List[str], sample_data: List[List[str]], max_rows: int = 5) -> str:
        """Format sample data for display in the prompt."""
        if not sample_data:
            return "No sample data available"
        
        formatted_rows = []
        for i, row in enumerate(sample_data[:max_rows]):
            # Create a dictionary for each row, handling cases where row length doesn't match headers
            row_dict = {}
            for j, header in enumerate(headers):
                value = row[j] if j < len(row) else ""
                # Truncate long values for readability
                if len(str(value)) > 50:
                    value = str(value)[:47] + "..."
                row_dict[header] = value
            
            formatted_rows.append(f"Row {i+1}: {row_dict}")
        
        return "\n".join(formatted_rows)
    
    def _create_functions_documentation(self) -> str:
        """Create documentation for available transformation functions."""
        functions_text = "\nAVAILABLE TRANSFORMATION FUNCTIONS:\n"
        for func, description in self.transformation_functions.items():
            if func in ['Upper', 'Lower', 'Trim', 'Title']:
                functions_text += f"- {func}(field) - {description}\n"
            elif func == 'Substring':
                functions_text += f"- {func}(field, start, length) - {description}\n"
            elif func == 'Replace':
                functions_text += f"- {func}(field, old_value, new_value) - {description}\n"
            elif func == 'Concatenate':
                functions_text += f"- {func}(field1, field2, ...) - {description}\n"
            elif func in ['Left', 'Right']:
                functions_text += f"- {func}(field, n) - {description}\n"
            else:
                functions_text += f"- {func}(field) - {description}\n"
        
        return functions_text
    
    def _call_databricks_api(self, prompt: str) -> Dict[str, Any]:
        """Make API call to Databricks endpoint using OpenAI client."""
        if not self.config.token:
            raise ValueError("Databricks API token is required.")
        client = openai.OpenAI(
            api_key=self.config.token,
            base_url=self.config.base_url
        )
        response = client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are a data mapping expert specializing in healthcare data. Always respond with valid JSON containing mappings and reasoning."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        # Convert OpenAI response to dict for compatibility
        return {"choices": [{"message": {"content": response.choices[0].message.content}}]}
    
    def _parse_llm_response(self, api_response: Dict[str, Any]) -> Dict[str, str]:
        """Parse Databricks API response to extract mappings."""
        
        try:
            # Extract content from API response
            content = api_response['choices'][0]['message']['content']
            
            # Try to parse as JSON first
            if content.strip().startswith('{'):
                result = json.loads(content)
                return result.get('mappings', {})
            
            # If not JSON, try to extract mappings using pattern matching
            return self._extract_mappings_from_text(content)
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Error parsing LLM response: {e}")
            return {}
    
    def _extract_mappings_from_text(self, content: str) -> Dict[str, str]:
        """Extract mappings from text response using pattern matching."""
        mappings = {}
        lines = content.split('\n')
        
        for line in lines:
            # Look for patterns like: "field": "mapping" or field: mapping
            if ':' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    field = parts[0].strip().strip('"').strip("'")
                    mapping = parts[1].strip().strip('"').strip("'").strip(',')
                    
                    # Only include if field is in our stage fields list
                    if field and mapping and any(char.isalpha() for char in field):
                        mappings[field] = mapping
        
        return mappings
    
    def _extract_reasoning(self, api_response: Dict[str, Any]) -> str:
        """Extract reasoning from LLM response."""
        try:
            content = api_response['choices'][0]['message']['content']
            
            if content.strip().startswith('{'):
                result = json.loads(content)
                return result.get('reasoning', 'No reasoning provided')
            else:
                # Look for reasoning in text
                lines = content.split('\n')
                for line in lines:
                    if 'reasoning' in line.lower() and ':' in line:
                        return line.split(':', 1)[1].strip()
                return 'Mappings generated based on field analysis'
                
        except Exception:
            return 'No reasoning available'
    
    def update_config(self, base_url: str = None, model: str = None):
        """Update Databricks configuration."""
        if base_url:
            self.config.base_url = base_url
        if model:
            self.config.model = model


# Convenience function for simple usage
def generate_mappings(source_headers: List[str], source_data_sample: List[List[str]], 
                     stage_fields: List[str], _databricks_url: str = None, _model: str = None, token: str = None) -> Dict[str, Any]:
    """
    Generate mappings using Databricks LLM. All config is hardcoded for Databricks. Make necessary transformations like casting date, calculating addinational details required for domain model.
    Args:
        source_headers: List of source file column headers
        source_data_sample: Sample rows from source data
        stage_fields: List of target stage field names
        token: Databricks API token
    Returns:
        Dictionary containing success status, mappings, and reasoning
    """
    config = LLMMapperConfig(token=token)
    mapper = LLMMapper(config)
    return mapper.generate_mappings(source_headers, source_data_sample, stage_fields)
