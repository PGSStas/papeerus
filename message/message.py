class MessageSerializer:
    def serialize(self, message, type):
        if type == 'text':
            return type + message
        if type == "picture":
            data = open(file=message, mode="rb").read()
            binary_str = ""
            for i in data:
                binary_str += str(i // 100)
                binary_str += str((i // 10) % 10)
                binary_str += str(i % 10)
            # print((type+binary_str).__class__)
            return (type + binary_str)
        if type == "video":
            data = open(file=message, mode="rb").read()
            binary_str = ""
            for i in data:
                binary_str += str(i // 100)
                binary_str += str((i // 10) % 10)
                binary_str += str(i % 10)
            # print((type+binary_str).__class__)
            return (type + binary_str)

    def deserialize(self, message: str):
        if len(message) > 4 and message[:4] == "text":
            return ["text", message[4:]]
        if len(message) > 7 and message[:7] == "picture":
            arr = bytearray()
            i = 7
            while i < len(message):
                arr.append(int(message[i]) * 100 + int(message[i + 1]) * 10 + int(message[i + 2]))
                i += 3
            kek = open(file="brat.jpg", mode="wb").write(arr)
            return ["picture", "42"]
        if len(message) > 5 and message[:5] == "video":
            arr = bytearray()
            i = 5
            while i < len(message):
                arr.append(int(message[i]) * 100 + int(message[i + 1]) * 10 + int(message[i + 2]))
                i += 3
            kek = open(file="video.mp4", mode="wb").write(arr)
            return ["video", "42"]
