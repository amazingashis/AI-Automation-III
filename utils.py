import pandas as pd

def parse_data_dict(path):
    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]
    column_mapping = {
        'Column Name': 'column_name',
        'Data Type': 'data_type',
        'Description': 'description',
        'Format': 'format',
        'Required': 'required',
        'Notes': 'notes'
    }
    df = df.rename(columns=column_mapping)
    if 'column_name' in df.columns:
        df = df.dropna(subset=['column_name'])
        instruction_patterns = ['instruction', 'this table', 'all fields', 'for actual', 'note:', 'example']
        for pattern in instruction_patterns:
            df = df[~df['column_name'].astype(str).str.contains(pattern, case=False, na=False)]
    return df

def parse_domain_model(path):
    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]
    column_mapping = {
        'Column Name': 'column_name',
        'Data Type': 'data_type',
        'Description': 'description',
        'Allowed Values / Format': 'allowed_values',
        'Required': 'required',
        'Notes': 'notes'
    }
    df = df.rename(columns=column_mapping)
    if 'column_name' in df.columns:
        df = df.dropna(subset=['column_name'])
    return df
