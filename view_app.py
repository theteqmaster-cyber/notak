with open('nserver/static/app.js', 'r') as f:
    js = f.read()
    
start = js.find('async function saveNote_wysiwyg')
end = js.find('function edCmd', start)
print(js[start:end])
