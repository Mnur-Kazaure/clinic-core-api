from app.schemas.bed import BedAssignRequest, BedTransferRequest


def test_bed_write_requests_do_not_expose_break_glass_reason():
    assign_properties = BedAssignRequest.model_json_schema()["properties"]
    transfer_properties = BedTransferRequest.model_json_schema()["properties"]

    assert "break_glass_reason" not in assign_properties
    assert "break_glass_reason" not in transfer_properties

    assert "break_glass" in assign_properties
    assert "break_glass" in transfer_properties
