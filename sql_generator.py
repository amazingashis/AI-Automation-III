# Use the same parsing utilities as app.py
from utils import parse_domain_model, parse_data_dict
# --- LLM Prompt Builder for SQL Script Generation ---

def build_llm_sql_prompt(source_table: str, mappings: dict, domain_model_path: str, data_dict_path: str) -> str:
    """
    Build a prompt for the LLM to generate all SQL scripts, using the same parsing logic and files as app.py.
    """
    # Read the full contents of the files (Excel or text)
    import os
    import pandas as pd
    def file_to_text(path):
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.xlsx', '.xls']:
            try:
                df = pd.read_excel(path)
                return df.to_csv(index=False)
            except Exception as e:
                return f"[ERROR reading Excel: {e}]"
        else:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"[ERROR reading file: {e}]"

    domain_model_text = file_to_text(domain_model_path)
    data_dict_text = file_to_text(data_dict_path)
    mapping_lines = [f"- {k}: {v}" for k, v in mappings.items()]
    # Try to load a 20-row sample from the source data if available
    source_sample = ''
    import os
    import pandas as pd
    # Try CSV and Excel extensions
    for ext in ['.csv', '.xlsx', '.xls']:
        sample_path = os.path.join('source_file', f'{source_table}{ext}') if not source_table.endswith(ext) else source_table
        if os.path.exists(sample_path):
            try:
                if ext == '.csv':
                    df = pd.read_csv(sample_path)
                else:
                    df = pd.read_excel(sample_path)
                source_sample = df.head(20).to_csv(index=False)
                break
            except Exception:
                pass
    if source_sample:
        sample_text = f"\nSample Source Data (first 20 rows):\n{source_sample}\n"
    else:
        sample_text = ''

    prompt = f'''
You are a US health care data analyst who is an expert in writing SQL scripts for US health care data standardization. Given the following context, generate all SQL scripts (including any necessary imports, table creation, transformation, mapping, and unload/export statements) to transform and standardize data from the source table to the domain model.

Source Table: {source_table}
{sample_text}
Source Data Dictionary (full file):
{data_dict_text}

Domain Model (full file):
{domain_model_text}

Field Mappings:
{chr(10).join(mapping_lines)}

Requirements:
- Generate all necessary SQL scripts to:
    1. Create the domain model table with correct data types.
    2. Transform and standardize data from the source table, including any required trims, type casts, and value mappings.
    3. Map source fields to domain model fields as per the mappings.
    4. Standardize outputs as per the data dictionary.
    5. Include any necessary SQL imports or setup statements for the target platform (e.g., Snowflake, Redshift, BigQuery, etc.).
    6. Provide an unload/export statement to export the final table.
- Output the SQL scripts in logical, well-commented blocks. Create full separate codes for each transformation.
- Do not include any explanations or extra text, only the SQL code and comments.
'''
    return prompt
import json
import pandas as pd
import os
from typing import List, Dict, Any

def load_domain_model(domain_model_path: str) -> pd.DataFrame:
    """Load the domain model Excel file as a DataFrame."""
    return pd.read_excel(domain_model_path)

def load_data_dict(data_dict_path: str) -> pd.DataFrame:
    """Load the data dictionary Excel file as a DataFrame."""
    return pd.read_excel(data_dict_path)

def load_mappings(mappings_path: str) -> Dict[str, Any]:
    """Load the saved mappings from JSON file."""
    with open(mappings_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def sql_type_from_domain(domain_type: str) -> str:
    """Map domain model data types to SQL types (simple version, extend as needed)."""
    mapping = {
        'string': 'VARCHAR(255)',
        'int': 'INTEGER',
        'float': 'FLOAT',
        'date': 'DATE',
        'datetime': 'TIMESTAMP',
        'boolean': 'BOOLEAN',
    }
    return mapping.get(domain_type.lower(), 'VARCHAR(255)')

def generate_create_table(domain_df: pd.DataFrame, table_name: str) -> str:
    """Generate CREATE TABLE statement from domain model DataFrame."""
    cols = []
    for _, row in domain_df.iterrows():
        col_name = row.get('FieldName') or row.get('field') or row.get('name')
        col_type = sql_type_from_domain(str(row.get('Type') or row.get('type') or 'string'))
        cols.append(f"    {col_name} {col_type}")
    cols_str = ',\n'.join(cols)
    return f"CREATE TABLE {table_name} (\n{cols_str}\n);"

def generate_transform_select(mappings: Dict[str, Any], domain_df: pd.DataFrame, data_dict_df: pd.DataFrame, source_table: str) -> str:
    """Generate SELECT statement with transformations and standardizations."""
    select_lines = []
    for _, row in domain_df.iterrows():
        domain_field = row.get('FieldName') or row.get('field') or row.get('name')
        source_field = mappings.get(domain_field, domain_field)
        # Example transformation: trim strings
        domain_type = str(row.get('Type') or row.get('type') or 'string').lower()
        if domain_type == 'string':
            expr = f"TRIM({source_field}) AS {domain_field}"
        else:
            expr = f"{source_field} AS {domain_field}"
        # Standardization (example: use data dict for value mapping)
        # Extend here as needed
        select_lines.append(expr)
    select_str = ',\n    '.join(select_lines)
    return f"SELECT\n    {select_str}\nFROM {source_table};"

def generate_unload(table_name: str, output_path: str = '/tmp/unload/') -> str:
    """Generate UNLOAD statement (example for Redshift/Snowflake, adjust as needed)."""
    return f"UNLOAD ('SELECT * FROM {table_name}') TO '{output_path}{table_name}/' CREDENTIALS 'aws_access_key_id=...;aws_secret_access_key=...' FORMAT AS PARQUET;"

def generate_sql_scripts(
    source_table: str,
    mappings_path: str,
    domain_model_path: str,
    data_dict_path: str,
    output_table: str = 'output_Table',
    unload_path: str = '/tmp/unload/'
) -> List[str]:
    """
    Generate SQL scripts in logical chunks for UI display and notebook export.
    Returns a list of SQL script strings.
    """
    domain_df = load_domain_model(domain_model_path)
    data_dict_df = load_data_dict(data_dict_path)
    mappings = load_mappings(mappings_path)

    # Build LLM prompt
    prompt = build_llm_sql_prompt(source_table, mappings, domain_model_path, data_dict_path)
    print("[DEBUG] LLM Prompt for SQL Generation:\n", prompt)

    # Call LLM (replace with your LLM call, e.g., Databricks, LMStudio, etc.)
    try:
        from llm_mapper import call_llm_for_sql
        llm_response = call_llm_for_sql(prompt)
        print("[DEBUG] LLM Response for SQL Generation:\n", llm_response)
        # Return LLM response as a single SQL chunk for now
        return [llm_response]
    except ImportError:
        print("[WARN] llm_mapper.call_llm_for_sql not implemented, falling back to legacy SQL generation.")
        create_table_sql = generate_create_table(domain_df, output_table)
        transform_select_sql = generate_transform_select(mappings, domain_df, data_dict_df, source_table)
        unload_sql = generate_unload(output_table, unload_path)
        # Insert/CTAS statement (legacy)
        return [
            '-- 1. Create Domain Model Table',
            create_table_sql,
            '',
            '-- 2. Transform and Map Source Data',
            transform_select_sql,
            '',
            '-- 3. Unload/Export Data',
            unload_sql
        ]

# Example usage (for testing):
# sql_chunks = generate_sql_scripts(
#     source_table='silver.elig',
#     mappings_path='mappings.json',
#     domain_model_path='domain_model.xlsx',
#     data_dict_path='data_dict.xlsx'
# )
# for chunk in sql_chunks:
#     print(chunk)
