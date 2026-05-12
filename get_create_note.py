with open('nserver/static/app.js', 'r') as f:
    js = f.read()
start = js.find('function createNewNoteInVault(')
if start != -1:
    end = js.find('}', start)
    print(js[start:end+1])
else:
    print("Function not found")
