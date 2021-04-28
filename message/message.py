class MessageSerializer:
    def serializeMessage(self, message, type):
        if type == 'text':
            ans = bytearray()
            ans += b'0'
            ans += message.encode()
            return ans
        if type == "picture":
            data = open(file=message, mode="rb").read()
            ans = bytearray()
            ans += b'1'
            ans += data
            return ans
        if type == "video":
            data = open(file=message, mode="rb").read()
            ans = bytearray()
            ans += b'2'
            ans += data
            return ans

    def deserializeMessage(self, message: bytes):
        if len(message) > 0 and message[0] == 48:
            return ["text", message[1:].decode()]
        if len(message) > 0 and message[0] == 49:
            arr = message[1:]
            kek = open(file="brat.jpg", mode="wb").write(arr)
            return ["picture", "42"]
        if len(message) > 0 and message[0] == 50:
            arr = message[1:]
            kek = open(file="video.mp4", mode="wb").write(arr)
            return ["video", "42"]
