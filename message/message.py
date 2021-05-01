class MessageSerializer:
    def serialize_message(self, message, type):
        if type == 'text':
            return b'0' + message.encode()

        if type == "picture":
            data = open(file=message, mode="rb").read()
            return b'1' + data

        if type == "video":
            data = open(file=message, mode="rb").read()
            return b'2' + data

    def deserialize_message(self, message: bytes):
        if len(message) > 0 and message[0] == 48:
            return ["text", message[1:].decode()]
        if len(message) > 0 and message[0] == 49:
            arr = message[1:]
            open(file="brat.jpg", mode="wb").write(arr)
            return ["picture", "42"]
        if len(message) > 0 and message[0] == 50:
            arr = message[1:]
            open(file="video.mp4", mode="wb").write(arr)
            return ["video", "42"]
