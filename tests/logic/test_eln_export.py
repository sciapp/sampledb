from sampledb.logic.eln_export import _unpack_single_item_arrays

def test_unpack_single_item_arrays():
    assert _unpack_single_item_arrays(1) == 1
    assert _unpack_single_item_arrays("A") == "A"
    assert _unpack_single_item_arrays([]) == []
    assert _unpack_single_item_arrays([1]) == 1
    assert _unpack_single_item_arrays([[1]]) == 1
    assert _unpack_single_item_arrays([1, 2]) == [1, 2]
    assert _unpack_single_item_arrays([[1], [2]]) == [1, 2]
    assert _unpack_single_item_arrays([[1, 2]]) == [1, 2]
    assert _unpack_single_item_arrays({}) == {}
    assert _unpack_single_item_arrays({"a": []}) == {"a": []}
    assert _unpack_single_item_arrays({"a": [1]}) == {"a": 1}
    assert _unpack_single_item_arrays({"a": [1, 2]}) == {"a": [1, 2]}
