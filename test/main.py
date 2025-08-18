import os
from llm_mapper import generate_mappings
from dotenv import load_dotenv

load_dotenv()

# Databricks API token from environment
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')

# Stage fields (target fields)
STAGE_FIELDS = [
    'memberFirst', 'memberLast', 'mbrDOB', 'mbrGender', 'ssn', 'memberID',
    'enrollmentStatus', 'enrollmentEffectiveDate', 'terminationDate', 'planID',
    'product', 'lob', 'memberMonth', 'dualEligibilityInd',
    'coverageDesc',
    'Employer Group: groupName',
    'Employer Group: groupStatus',
    'Employer Group: addressLine1',
    'Employer Group: addressLine2',
    'Employer Group: zip'
]


# Read source headers and first 10 rows from the CSV file
import csv
CSV_PATH = os.path.join(os.path.dirname(__file__), '../source_file/member_enrollment_file.csv')
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    SOURCE_HEADERS = next(reader)
    SOURCE_DATA_SAMPLE = [row for _, row in zip(range(10), reader)]

# Transformation rules (for context)
TRANSFORMATION_RULES = {
    'Trim': 'strip()',
    'Upper': 'upper()',
    'Lower': 'lower()',
    'Title': 'title()',
    'Left': 'left(n)',
    'Right': 'right(n)',
    'Substring': 'substring(start, length)',
    'Replace': 'replace(old, new)',
    'Concatenate': 'concatenate(field1, field2)',
    'DateFormat': 'date_format(format)',
    'IsNull': 'is_null()',
    'NotNull': 'not_null()',
    'Length': 'length()',
    'Contains': 'contains(substring)',
    'Array': 'array(field1, field2, ...)'  # Added array transformation
}

# Domain model and data dictionary context (as strings for LLM prompt)
DOMAIN_MODEL = """
Eligibility Domain Model:
- memberFirst: First name of the member
- memberLast: Last name of the member
- mbrDOB: Date of birth
- mbrGender: Gender
- ssn: Social Security Number
- memberID: Unique member identifier
- enrollmentStatus: Enrollment status
- enrollmentEffectiveDate: Enrollment effective date
- terminationDate: Termination date
- planID: Plan identifier
- product: Product type
- lob: Line of business
- memberMonth: Number of member months
- dualEligibilityInd: Dual eligibility indicator
- coverageDesc: Coverage description
- Employer Group: Employer group (array groupName (Name of the employer group), groupStatus (Status of the group), addressLine1 (First line of address), addressLine2 (Second line of address), zip (ZIP code))
"""

DATA_DICTIONARY = """
Source Data Dictionary:
MemberID : Unique identifier for the member
SSN : Social Security Number (masked/fake for demo)
FirstName : Member first name
LastName : Member last name
Gender : Member gender
DOB : Member date of birth
Address : Member street address
City : Member city
State : Member state
Zip : Member ZIP code
Phone : Member phone number
Email : Member email address
EnrollmentStart : Coverage enrollment start date
EnrollmentEnd : Coverage enrollment end date
Relationship : Relationship to subscriber
MemberSeq : Sequence in the family unit
CoverageType : Type of benefit coverage
CoverageStatus : Status of the coverage
GroupID : Unique identifier for employer/group
GroupName : Name of the employer/group
GroupAddress : Employer/group address
GroupCity : Employer/group city
GroupState : Employer/group state
GroupZip : Employer/group ZIP code
GroupStatus : Status of the employer/group
PlanID : Insurance plan identifier
PlanName : Insurance plan name
PlanType : Plan type abbreviation
PlanEffectiveDate : Date plan became effective
PlanTerminationDate : Date plan is/was terminated
PCPName : Primary Care Physician name
PCPNPI : National Provider Identifier for PCP
SubscriberID : MemberID of the subscriber in the family unit
MaritalStatus : Member marital status
EmploymentStatus : Member employment status
Language : Preferred language
Ethnicity : Member ethnicity
MedicareID : Medicare Identifier (if any)
MedicaidID : Medicaid Identifier (if any)
OtherInsurance : Indicates presence of other insurance
DisabilityStatus : Indicates disability status
"""

def main():
    print("Testing Databricks LLM mapping...")
    # Compose extra context for LLM prompt
    extra_context = f"""
{DOMAIN_MODEL}\n\n{DATA_DICTIONARY}\n\nTransformation Rules:\n{TRANSFORMATION_RULES}\n\nFor each transformation rule, also generate a sample SQL script that demonstrates how to implement that transformation in Databricks SQL (ANSI SQL compatible with Databricks).\n\nPlease provide the SQL mapping expressions for each stage field using the transformation rules, based on the source data sample. Respond in JSON with 'mappings', 'reasoning', and 'sql_scripts' (where 'sql_scripts' is a dictionary with the transformation rule as the key and the SQL script as the value, and all SQL must be valid in Databricks SQL).\n"""
    # Call the LLM mapping generator
    result = generate_mappings(
        SOURCE_HEADERS,
        SOURCE_DATA_SAMPLE,
        STAGE_FIELDS,
        token=DATABRICKS_TOKEN
    )
    print("\nLLM Output:")
    print(result)

if __name__ == "__main__":
    main()
