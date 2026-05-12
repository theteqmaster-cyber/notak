with open('nserver/static/app.js', 'r') as f:
    js = f.read()
start = js.find('function navigate(')
end = js.find('}', start)
print(js[start:end+1])
