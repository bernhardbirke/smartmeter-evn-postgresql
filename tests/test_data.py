import pytest
from src.smartmeter.postgresql_tasks import PostgresTasks
from src.smartmeter.config import Configuration
from src.smartmeter.data import SmartmeterToPostgres


# create instance of Class SmartmeterToPostgres
@pytest.fixture
def smartmeterpostgres():
    config = Configuration()
    client = PostgresTasks()
    return SmartmeterToPostgres(config, client)


# evn test  based on the official documentation "218_13_SmartMeter_Kundenschnittstelle_2604_web.pdf"
@pytest.fixture
def evn_smartmeterpostgres(smartmeterpostgres):
    smartmeterpostgres.config_env["evn_key"] = "36C66639E48A8CA4D6BC8B282A793BBB"
    return smartmeterpostgres


@pytest.fixture
def evn_sample_data():
    evn_encrypted_apdu = "68FAFA6853FF000167DB084B464D675000000981F8200000002388D5AB4F97515AAFC6B88D2F85DAA7A0E3C0C40D004535C397C9D037AB7DBDA329107615444894A1A0DD7E85F02D496CECD3FF46AF5FB3C9229CFE8F3EE4606AB2E1F409F36AAD2E50900A4396FC6C2E083F373233A69616950758BFC7D63A9E9B6E99E21B2CBC2B934772CA51FD4D69830711CAB1F8CFF25F0A329337CBA51904F0CAED88D61968743C8454BA922EB00038182C22FE316D16F2A9F544D6F75D51A4E92A1C4EF8AB19A2B7FEAA32D0726C0ED80229AE6C0F7621A4209251ACE2B2BC66FF0327A653BB686C756BE033C7A281F1D2A7E1FA31C3983E15F8FD16CC5787E6F517166814146853FF110167419A3CFDA44BE438C96F0E38BF83D98316"
    evn_decrypted_apdu = "0F8006870E0C07E5091B01092F0F00FF88800223090C07E5091B01092F0F00FF888009060100010800FF060000328902020F00161E09060100020800FF060000000002020F00161E09060100010700FF060000000002020F00161B09060100020700FF060000000002020F00161B09060100200700FF12092102020FFF162309060100340700FF12000002020FFF162309060100480700FF12000002020FFF1623090601001F0700FF12000002020FFE162109060100330700FF12000002020FFE162109060100470700FF12000002020FFE1621090601000D0700FF1203E802020FFD16FF090C313831323230303030303039"
    my_decrypted_apdu = "0f8006870e0c07e5091b01092f0f00ff88800223090c07e5091b01092f0f00ff888009060100010800ff060000328902020f00161e09060100020800ff060000000002020f00161e09060100010700ff060000000002020f00161b09060100020700ff060000000002020f00161b09060100200700ff12092102020fff162309060100340700ff12000002020fff162309060100480700ff12000002020fff1623090601001f0700ff12000002020ffe162109060100330700ff12000002020ffe162109060100470700ff12000002020ffe1621090601000d0700ff1203e802020ffd16a985"
    return {
        "evn_encrypted_apdu": evn_encrypted_apdu,
        "evn_decrypted_apdu": evn_decrypted_apdu,
        "my_decrypted_apdu": my_decrypted_apdu,
    }


def test_split_hex_string_1(evn_smartmeterpostgres, evn_sample_data):
    encrypted_dict = evn_smartmeterpostgres.split_hex_string(
        evn_sample_data["evn_encrypted_apdu"]
    )
    assert encrypted_dict["mbusstart"] == "68FAFA68"


def test_split_hex_string_2(evn_smartmeterpostgres, evn_sample_data):
    encrypted_dict = evn_smartmeterpostgres.split_hex_string(
        evn_sample_data["evn_encrypted_apdu"]
    )
    assert (
        encrypted_dict["frame"]
        == "88D5AB4F97515AAFC6B88D2F85DAA7A0E3C0C40D004535C397C9D037AB7DBDA329107615444894A1A0DD7E85F02D496CECD3FF46AF5FB3C9229CFE8F3EE4606AB2E1F409F36AAD2E50900A4396FC6C2E083F373233A69616950758BFC7D63A9E9B6E99E21B2CBC2B934772CA51FD4D69830711CAB1F8CFF25F0A329337CBA51904F0CAED88D61968743C8454BA922EB00038182C22FE316D16F2A9F544D6F75D51A4E92A1C4EF8AB19A2B7FEAA32D0726C0ED80229AE6C0F7621A4209251ACE2B2BC66FF0327A653BB686C756BE033C7A281F1D2A7E1FA31C3983E15F8FD16CC5787E6F51716"
    )


def test_evn_key(evn_smartmeterpostgres):
    key = evn_smartmeterpostgres.config_env["evn_key"]
    assert key == "36C66639E48A8CA4D6BC8B282A793BBB"


def t_decrypt_apdu(evn_smartmeterpostgres, evn_sample_data):
    frame = "88D5AB4F97515AAFC6B88D2F85DAA7A0E3C0C40D004535C397C9D037AB7DBDA329107615444894A1A0DD7E85F02D496CECD3FF46AF5FB3C9229CFE8F3EE4606AB2E1F409F36AAD2E50900A4396FC6C2E083F373233A69616950758BFC7D63A9E9B6E99E21B2CBC2B934772CA51FD4D69830711CAB1F8CFF25F0A329337CBA51904F0CAED88D61968743C8454BA922EB00038182C22FE316D16F2A9F544D6F75D51A4E92A1C4EF8AB19A2B7FEAA32D0726C0ED80229AE6C0F7621A4209251ACE2B2BC66FF0327A653BB686C756BE033C7A281F1D2A7E1FA31C3983E15F8FD16CC5787E6F51716"
    key = evn_smartmeterpostgres.config_env["evn_key"]
    system_titel = evn_sample_data["evn_encrypted_apdu"][22:38]
    frame_counter = evn_sample_data["evn_encrypted_apdu"][44:52]
    decrypted = evn_smartmeterpostgres.decrypt_apdu(
        frame, key, system_titel, frame_counter
    )
    assert decrypted == evn_sample_data["evn_decrypted_apdu"]


def t_decrypt_apdu_2(evn_smartmeterpostgres, evn_sample_data):
    encrypted_dict = evn_smartmeterpostgres.split_hex_string(
        evn_sample_data["evn_encrypted_apdu"]
    )
    key = evn_smartmeterpostgres.config_env["evn_key"]
    apdu = evn_smartmeterpostgres.decrypt_apdu(
        encrypted_dict["frame"],
        key,
        encrypted_dict["system_titel"],
        encrypted_dict["frame_counter"],
    )
    assert apdu == evn_sample_data["evn_decrypted_apdu"]


def test_translate_dlms_1(evn_smartmeterpostgres, evn_sample_data):
    evn_smartmeterpostgres.translate_dlms(evn_sample_data["evn_decrypted_apdu"])
    assert evn_smartmeterpostgres.data["WirkenergieP"] == 12937


def test_translate_dlms_2(evn_smartmeterpostgres, evn_sample_data):
    evn_smartmeterpostgres.translate_dlms(evn_sample_data["evn_decrypted_apdu"])
    assert round(evn_smartmeterpostgres.data["SpannungL1"], 2) == 233.7


def test_translate_dlms_3(evn_smartmeterpostgres, evn_sample_data):
    evn_smartmeterpostgres.translate_dlms(evn_sample_data["my_decrypted_apdu"])
    assert evn_smartmeterpostgres.data["WirkenergieP"] == 12937
