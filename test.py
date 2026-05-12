with open('nserver/static/index.html', 'r') as f:
    text = f.read()
start = text.find('id="page-music"')
if start != -1:
    end = text.find('</section>', start)
    print(text[start:end+10])
else:
    print("Not found")
