"""Action intents: the fields client/desktop_app.py dispatches on."""
import pytest


@pytest.mark.parametrize(
    ("text", "expected_target"),
    [
        ("open notepad", "notepad"),
        ("open chrome", "chrome"),
        ("open calculator", "calculator"),
        ("open youtube", "youtube"),
        ("launch whatsapp", "whatsapp"),
    ],
)
async def test_launch_intents(client, text, expected_target):
    response = await client.post("/execute", json={"text": text})
    body = response.json()
    assert body["handled"] is True
    assert body["action"] == "launch"
    assert body["action_target"] == expected_target


async def test_open_this_uses_selected_action(client):
    response = await client.post(
        "/execute", json={"text": "open this", "selected_action": "calculator"}
    )
    body = response.json()
    assert body["action"] == "launch"
    assert body["action_target"] == "calculator"


async def test_open_that_uses_last_action(client):
    response = await client.post(
        "/execute", json={"text": "open that", "last_action": "youtube"}
    )
    body = response.json()
    assert body["action"] == "launch"
    assert body["action_target"] == "youtube"


async def test_unknown_launch_target_is_reported_not_dispatched(client):
    response = await client.post("/execute", json={"text": "open photoshop"})
    body = response.json()
    assert body["handled"] is True
    assert body["action"] is None
    assert "photoshop" in body["response"]


@pytest.mark.parametrize(
    ("text", "expected_target"),
    [
        ("play the music", "play"),
        ("stop the music", "stop"),
        ("restart the theme", "restart"),
    ],
)
async def test_music_intents(client, text, expected_target):
    response = await client.post("/execute", json={"text": text})
    body = response.json()
    assert body["action"] == "music"
    assert body["action_target"] == expected_target


async def test_create_folder_intent(client):
    response = await client.post("/execute", json={"text": "create a folder named projects"})
    body = response.json()
    assert body["action"] == "file_op"
    assert body["action_target"] == "create_folder"
    assert body["action_data"]["name"] == "projects"


async def test_create_file_intent_gets_text_extension(client):
    response = await client.post("/execute", json={"text": "create a file named shopping"})
    body = response.json()
    assert body["action_target"] == "create_file"
    assert body["action_data"]["name"] == "shopping.txt"


async def test_write_file_intent_carries_content(client):
    response = await client.post("/execute", json={"text": "write buy milk into groceries"})
    body = response.json()
    assert body["action_target"] == "write_file"
    assert body["action_data"]["name"] == "groceries.txt"
    assert body["action_data"]["content"] == "buy milk"


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("../../etc/passwd", "etcpasswd"),
        ("notes/../secret", "notes.. secret".replace(" ", "")),
    ],
)
async def test_file_names_are_sanitized_against_traversal(client, raw_name, expected):
    """_sanitize_name strips path separators so a spoken name can't escape
    the client's notes/ directory."""
    response = await client.post("/execute", json={"text": f"create a folder named {raw_name}"})
    name = response.json()["action_data"]["name"]
    assert "/" not in name
    assert "\\" not in name
