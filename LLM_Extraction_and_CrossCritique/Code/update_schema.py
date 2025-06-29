import csv
import json

# Step 1: Read Definitions.csv into a dictionary
definitions = {}
with open('LLM_Extraction_and_CrossCritique/Code/Definitions.csv', 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        definitions[row['Column Name']] = row['Definition']

# Step 2: Load the JSON schema
with open('LLM_Extraction_and_CrossCritique/Code/w2-schema.json', 'r', encoding='utf-8') as jsonfile:
    schema = json.load(jsonfile)

# Step 3: Update descriptions in the schema and track unused definitions
updated_count = 0
used_definitions = set()
for field_name, field_data in schema['properties']['clinical_trial_data']['items']['properties'].items():
    if field_name in definitions:
        field_data['description'] = definitions[field_name]
        used_definitions.add(field_name)
        updated_count += 1
    else:
        print(f"No definition found for field: {field_name}")

print(f"Updated descriptions for {updated_count} fields.")

# Step 4: Identify unused definitions
unused_definitions = set(definitions.keys()) - used_definitions
if unused_definitions:
    print("Unused definitions from Definitions.csv:")
    for unused in unused_definitions:
        print(f" - {unused}")
else:
    print("No unused definitions found.")

# Step 5: Add unused definitions as new fields in the schema
added_count = 0
for unused in unused_definitions:
    schema['properties']['clinical_trial_data']['items']['properties'][unused] = {
        "type": "string",
        "description": definitions[unused]
    }
    added_count += 1

print(f"Added {added_count} unused definitions as new fields in the schema.")

# Step 6: Save the updated schema to a new file
with open('LLM_Extraction_and_CrossCritique/Code/w3-schema.json', 'w', encoding='utf-8') as jsonfile:
    json.dump(schema, jsonfile, indent=2)

print("Updated schema saved to w3-schema.json")
