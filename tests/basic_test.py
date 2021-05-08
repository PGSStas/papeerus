import pytest
from message import message
from message.message import MessageSerializer
from chord.table_node import TableNode


def test_message():
    serializer = MessageSerializer()
    test1 = serializer.serialize_message("a", "text")
    test2 = serializer.serialize_message("aggfdgdfgfdgdfg", "text")
    long_test = "a" * 1000000
    test3 = serializer.serialize_message(long_test,"text")
    assert serializer.deserialize_message(test1) == ["text",'a']
    assert serializer.deserialize_message(test2) == ["text",'aggfdgdfgfdgdfg']
    assert serializer.deserialize_message(test3) == ["text",long_test]

def test_node():
    first = TableNode(21234)
    first.create_by_name("A")
    invite = first.generate_invite()
    assert invite[len(invite)-1] == 'A'
    second = TableNode(21235)
    second.establish_connection(invite)
    third = TableNode(21236)
    third.establish_connection(invite)
    print(42)



