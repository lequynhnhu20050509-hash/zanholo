import json


def read_setting_value(key):
    try:
        with open('seting.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
        return settings.get(key)
    except FileNotFoundError:
        print(
            f"Lỗi: Không tìm thấy file seting.json. Sử dụng giá trị mặc định cho {key}.")
        return None
    except json.JSONDecodeError:
        print(
            f"Lỗi: File seting.json không hợp lệ. Sử dụng giá trị mặc định cho {key}.")
        return None


def read_prefix():
    return read_setting_value('prefix') or "?"


def read_admin():
    return read_setting_value('admin') or "7376495146241444949"


def read_adm():
    return read_setting_value('adm')


IMEI = "79ab12a4-e03e-4e05-976a-d877cff79872-7ceed19ee5ebdbf792f56329591ffc53"
SESSION_COOKIES = {"__zi":"3000.SSZzejyD3yaynFwzpKGIpZ37_hRBJXo4FCRqkeG30SeothVcbWbFXZRR-wcH2qo1Df3ugf1EJeGodlggDpCv.1","__zi-legacy":"3000.SSZzejyD3yaynFwzpKGIpZ37_hRBJXo4FCRqkeG30SeothVcbWbFXZRR-wcH2qo1Df3ugf1EJeGodlggDpCv.1","_ga_YT9TMXZYV9":"GS2.1.s1768359799$o1$g1$t1768359831$j28$l0$h0","_ga":"GA1.2.380764859.1766907335","_zlang":"vn","_gid":"GA1.2.1555562022.1770647647","_ga_3EM8ZPYYN3":"GS2.2.s1770647648$o6$g0$t1770647648$j60$l0$h0","zpsid":"V-Lj.451337243.1.6k3xEFKAg43kravQ-GgeG81vsdJ0EvjpmZYSS_G-YsKW0Aezz6fOoPmAg40","zpw_sek":"R7dM.451337243.a0.H5fH1UPUkmZzWbqInrwx29rytcF4P9a-aGwBFCqvWp_GACX-YmlyOQ4S_s2tOuOgcr-FAyEBiGgRNzhuRpUx20","app.event.zalo.me":"2851268904615385880"}
API_KEY = 'api_key'
SECRET_KEY = 'secret_key'
PREFIX = read_prefix()
ADMIN = read_admin()
ADM = read_adm()
GEMINI_API_KEY = "AIzaSyDYBFbqf2Uti1IoZQA1fyWucKG5bqJAFvw"
