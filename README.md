# JBOB parser (Bobfob's JSON parser)

## Purpose of the project

My answer: why not?

## Usage

Just download single file, import module at your's python file and then you can use functions: *dump*, *parse* and *parse_string*.\
If Pylance is arguing then just turn it off 🤷‍♂️

## Example

> "./test_file.json"
```JSON
{
    "person1": {
        "name": "Mike",
        "age": 24,
        "confidential data": {
            "address": "Some Street 18",
            "phone number": "+1-212-456-7890"
        }
    }
}
```

```Python
import JbobParser as jbp

# Parsing with some file (parser doesn't looks at extension of the file)
parsed_json: jbp.JsonBlock = jbp.parse("./test_file.json")

print(parsed_json) # Outputs: {"person1": {"name": "Mike", "age": 24, "confidential data": {"address": "Some Street 18", "phone number": "+1-212-456-7890"}}}

parsed_json2: jbp.JsonBlock = jbp.parse_string("""
{
    "person1": {
        "name": "Mike",
        "age": 24,
        "confidential data": {
            "address": "Some Street 18",
            "phone number": "+1-212-456-7890"
        }
        
        // ...
    }
}
""")

print(parsed_json2) # will output the same result

# dumps function used for compressing JsonBlock object into string with provided indent
print(jbp.dump(parsed_json))

# You can assign some values to parsed json like dict object
parsed_json["person1"]["age"] = "25"

print(parsed_json) # will output same result but the age will be now string with value "25"

# like in dict object the JsonBlock provides items, keys and values functions

print(parsed_json.items()) # Outputs: [("person1", {"name": "Mike", "age": "25", ...})]

print(parsed_json.keys()) # Outputs: ["person1"]

print(parsed_json.values()) # Outputs: [{"name": "Mike", "age": "25", ...}]
```

## Thats all for now
