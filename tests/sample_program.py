import yoda.analyser

yoda.analyser.db.set_trace()

a = 1
b = 3
z = "hello"

for c in range(10):
    d = c
    print(c)

def spam(arg):
    result = arg*4
    return result

def spam2(arg):
    result = arg*4
    return result

x = spam(8)

b=4

x = spam2(18)
yoda.analyser.db.set_quit()

