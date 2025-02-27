# Read/Write Raw Responses from the File

def read_raw_responses(path):
    
    f = open(path)
    data = f.readlines()
    f.close()

    strings = ""
    results = []
    for i in data:
        if "###" not in i:
            strings += i
        elif "###" in i and len(i) < 5:
            results.append(strings)
            strings = ""
            
    return results

def write_raw_responses(results, response_recording):
    
    f = open(response_recording,'w')
        
    for result in results:
        r = result.split("\n")
        for i in r:
            f.writelines(i+"\n")
        f.writelines("\n###\n")
        
    f.close()