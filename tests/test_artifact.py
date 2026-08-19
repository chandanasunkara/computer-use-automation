from app.models import Capability


def test_artifact_contract():
    artifact = Capability(
        capability_id="member.lookup_savings_balance",
        description="lookup",
        target={"surface": "web", "application": "local-bank-demo"},
        inputs={"member_id": {"type": "string", "required": True}},
        outputs={"savings_balance": {"type": "number"}},
        steps=[],
        success_condition="balance exists",
    )
    assert artifact.schema_version == "1.0"
    assert artifact.inputs["member_id"]["type"] == "string"
