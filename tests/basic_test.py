import sys
import time

import pytest
from message import message
from message.message import MessageSerializer
from chord.table_node import TableNode
from io import StringIO
from bisect import bisect_right


def test_message():
    serializer = MessageSerializer()
    test1 = serializer.serialize_message("a", "text")
    test2 = serializer.serialize_message("aggfdgdfgfdgdfg", "text")
    long_test = "a" * 1000000
    test3 = serializer.serialize_message(long_test,"text")
    assert serializer.deserialize_message(test1) == ["text", 'a']
    assert serializer.deserialize_message(test2) == ["text", 'aggfdgdfgfdgdfg']
    assert serializer.deserialize_message(test3) == ["text", long_test]


def test_two_nodes_connection():
    first = TableNode(21234)
    first.create_by_name("A")
    invite = first.generate_invite()
    assert invite[len(invite)-1] == 'A'
    second = TableNode(21235)
    sys.stdin = StringIO("B")
    second.establish_connection(invite)
    time.sleep(4)
    assert second.successor == first._id
    assert second.predecessor == first._id
    assert first.successor == second._id
    assert first.predecessor == second._id


def test_nodes_connection():
    start_port = 10120
    first = TableNode(start_port)
    first.create_by_name("A")
    invite = first.generate_invite()
    nodes_num = 10
    nodes = [first]
    for i in range(66, 66 + nodes_num):
        print(first.finger_table)
        nodes.append(TableNode(start_port + (i - 66 + 1)))
        time.sleep(1)
        sys.stdin = StringIO(chr(65 + (i - 66 + 1)))
        nodes[-1].establish_connection(invite)
    time.sleep(3)
    nodes.sort(key=lambda a: a._id)
    for i in range(len(nodes)):
        print(nodes[i]._id, "->", nodes[i].successor)
        assert nodes[i].successor == nodes[(i + 1) % len(nodes)]._id

    # time.sleep(10)
    # print(first.finger_table)
    # print(list(map(lambda a: a._id, nodes)))
    # print(first._id)
    # for i in range(len(first.finger_table)):
    #     print(i)
    #     index = bisect_right(list(map(lambda a: a._id, nodes)), (first._id + 2**i) % 2**TableNode._m)
    #     assert nodes[index]._id == first.finger_table[i]









