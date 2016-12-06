# author ihyf
# coding:utf-8
import time
import os
import ConfigParser
import urllib2
import json
import simplejson
import hashlib
import pyaudio
import wave
import subprocess
SUCCESS = 1  # 成功
FAIL = 0  # 失败
SERVER_NERWORK_ERROR = 404  # 服务器网络错误
LOCAL_NERWORK_ERROR = 444  # 本地网络错误
STATE = 1  # 初始状态
ORDER_ID = []  # 订单号列表


def get_info():
    # 得到config信息
    info_data = {}
    try:
        config = ConfigParser.ConfigParser()
        path = os.path.abspath(os.curdir).split('/addons')[0] + '/info.conf'
        config.read(path)
        username = config.get('options', 'username')
        password = config.get('options', 'password')
        server_ip = config.get('options', 'server_ip')

        # m = hashlib.md5()
        # m.update(password)
        # password = m.hexdigest()  # 获得密码md5
        info_data['username'] = username
        info_data['password'] = password
        info_data['server_ip'] = server_ip
    except Exception:
        info_data['error'] = "获得config文件信息出错"
    return info_data
def update_info(new_info):
    # 修改config信息
    config = ConfigParser.ConfigParser()
    path = os.path.abspath(os.curdir).split('/addons')[0] + '/info.conf'
    config.read(path)
    config.set("options","password",new_info['new_password'])
    config.set("options", "server_ip", new_info['server_ip'])
    config.write(open(path, "w"))


def scanning_so(scanner_thread):
    # 扫描订单头,用户本地判断
    print "SO"
    order_id_barcode = get_scanner_thread_barcode(scanner_thread)  # 得到当前扫码枪里信息
    if order_id_barcode and 'SO' in order_id_barcode[:2]:
        ORDER_ID.append(order_id_barcode)  # 加入订单列表
        state = 2
        return state
    if order_id_barcode:
        #  播放语音 条形码记录为空
        wav_name = "play_qingsaodingdan.wav"
        wav_url = get_wav_url(wav_name)
        # play_the_wav(wav_url)
        use_mplayer_play_wav(wav_url)  # 使用mplayer播放

    state = 1
    return state


def scanning_action(scanner_thread):
    # 扫描发起的动作
    print "捡货"
    tip = {}
    request_data = {}
    info_data = get_info()
    request_data['username'] = info_data['username']
    request_data['password'] = info_data['password']
    request_data['server_ip'] = info_data['server_ip']
    action_barcode = get_scanner_thread_barcode(scanner_thread)  # 得到当前扫码枪里信息
    state = 1
    if action_barcode and 'SO' in action_barcode[:2]:  #
        ORDER_ID.append(action_barcode)  # 加入订单列表
        state = 2
        return state
    if action_barcode and 'jianhuo' in action_barcode:  # 捡货
        if ORDER_ID:
            # 播放语音 正在进行拣货操作
            wav_name = 'play_zhengzaijianhuo.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            order_id = ORDER_ID[-1].upper()  # 带验证的订单编号
            request_data['order_id'] = order_id
        else:
            # 播放语音 条形码记录为空
            wav_name = "play_qingsaodingdan.wav"
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            state = 1
            return state
        tip = request_to_server(request_data, 'jianhuo')
        if tip and 'error' in tip and tip['error']:
            state = 1
        elif tip and 'msg' in tip and tip['msg'] and tip['msg'] == 'jianhuo_success':
            state = 1
        elif tip and 'msg' in tip and tip['msg'] and tip['msg'] == 'fahuo_success':
            state = 1
        ORDER_ID[:] = []  # 有效订单号列表 重置为空
        return state

    elif action_barcode and 'fahuo' in action_barcode:  # 发货
        if ORDER_ID:
            # 播放语音 正在进行发货操作
            wav_name = 'play_zhengzaifahuo.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            order_id = ORDER_ID[-1].upper()  # 带验证的订单编号
            request_data['order_id'] = order_id
        else:
            # 播放语音 条形码记录为空
            wav_name = "play_qingsaodingdan.wav"
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            state = 1
            return state
        tip = request_to_server(request_data, 'fahuo')
        if tip and 'error' in tip and tip['error']:
            state = 1
        elif tip and 'msg' in tip and tip['msg'] and tip['msg'] == 'jianhuo_success':
            state = 1
        elif tip and 'msg' in tip and tip['msg'] and tip['msg'] == 'fahuo_success':
            state = 1
        ORDER_ID[:] = []  # 有效订单号列表 重置为空
        return state
    else:
        # 播放语音 第二次请扫描动作，请重扫订单
        state = 1
    return state


def request_to_server(reqeust_data,action_type):
    # 请求服务器,得到相应
    tip = {}
    headers = {'Content-Type': 'application/json'}
    url = reqeust_data['server_ip']+"/app_api/pos/stock_picking"
    reqeust_data['type'] = action_type
    data ={
        "jsonrpc": "2.0",
        "method": "call",
        "params": reqeust_data
    }
    # print "data"
    # print data
    try:
        request_action = urllib2.Request(url=url,
                                         headers=headers, data=json.dumps(data))
    except Exception:
        tip['error'] = "网络连接失败，请重试"
        wav_name = 'play_lianjieshibai.wav'
        wav_url = get_wav_url(wav_name)
        # play_the_wav(wav_url)
        use_mplayer_play_wav(wav_url)  # 使用mplayer播放
        # 播放语音 网络连接失败，请重试
        return tip
    try:
        response_data = urllib2.urlopen(request_action)
        res = response_data.read()
        res = simplejson.loads(res)
        if not res or not res['result']:
            tip['error'] = "服务器超时"
            wav_name = 'play_wangluochaoshi.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            # 播放语音 服务器超时
            return tip
    except Exception:
        tip['error'] = "服务器错误，请联系客服"
        # 播放语音 服务器错误，请联系客服
        wav_name = 'play_fuwuqicuowu.wav'
        wav_url = get_wav_url(wav_name)
        # play_the_wav(wav_url)
        use_mplayer_play_wav(wav_url)  # 使用mplayer播放
        return tip
    res = res['result']
    # print "hyf test"
    # print res
    tip = check_user_info(res)
    if tip and 'error' in tip and tip['error']:
        return tip
    elif tip and 'msg' in tip and tip['msg'] == 'check_user_success':
        if action_type == 'jianhuo':
            tip = check_jianhuo_order_info(res)
        elif action_type == 'fahuo':
            tip = check_fahuo_order_info(res)
        return tip


def get_scanner_thread_barcode(scanner_thread):
    # 得到扫码枪信息
    return scanner_thread.get_barcode() if scanner_thread else None


def check_user_info(data):
    tip = {}
    if 'user_check_info' in data and data['user_check_info']:
        if data['user_check_info'] == 'check_user_success':
            tip['msg'] = "check_user_success"
            return tip
        elif data['user_check_info'] == 'check_user_fail':
            tip['error'] = '认证失败'
            # 播放语音 用户认证失败
            wav_name = 'play_renzhengshibai.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            return tip
    else:
        tip['error'] = "服务器错误，请联系客服"
        # 播放语音 服务器错误，请联系客服
        wav_name = 'play_fuwuqicuowu.wav'
        wav_url = get_wav_url(wav_name)
        # play_the_wav(wav_url)
        use_mplayer_play_wav(wav_url)  # 使用mplayer播放
        return tip


def check_jianhuo_order_info(response_data):
    # 校验捡货订单
    tip = {}
    if 'order_check_jianhuo_info' in response_data \
        and response_data['order_check_jianhuo_info']:
        if response_data['order_check_jianhuo_info'] == 'no_order':
            # 播放语音 没有该订单
            tip['error'] = '没有该订单'
            wav_name = 'play_dingdanbucunzai.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            return tip
        elif response_data['order_check_jianhuo_info'] == 'jianhuo_success':
            # 播放语音 捡货成功
            wav_name = 'play_jianhuochenggong.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            tip['msg'] = 'jianhuo_success'
            return tip
        elif response_data['order_check_jianhuo_info'] == 'already_jianhuo':
            # 播放语音 该订单已捡货
            wav_name = 'play_dingdanyijianhuo.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            tip['error'] = '该订单已捡货'
            return tip
        elif response_data['order_check_jianhuo_info'] == 'already_fahuo':
            # 播放语音 该订单已发货
            wav_name = 'play_dingdanyifahuo.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            tip['error'] = '该订单已发货'
            return tip


def check_fahuo_order_info(response_data):
    # 校验发货订单
    tip = {}
    if 'order_check_fahuo_info' in response_data \
            and response_data['order_check_fahuo_info']:
        if response_data['order_check_fahuo_info'] == 'no_order':
            # 播放语音 没有该订单
            wav_name = 'play_dingdanbucunzai.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            tip['error'] = '没有该订单'
            return tip
        elif response_data['order_check_fahuo_info'] == 'need_jianhuo':
            # 播放语音 订单需要先捡货
            wav_name = 'play_dingdanxuxianjianhuo.wav'
            wav_url = get_wav_url(wav_name)
            play_the_wav(wav_url)
            tip['error'] = '订单需要先捡货'
            return tip
        elif response_data['order_check_fahuo_info'] == 'fahuo_success':
            # 播放语音 订单发货成功
            wav_name = 'play_dingdanfahuochenggong.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            tip['msg'] = '订单发货成功'
            return tip
        elif response_data['order_check_fahuo_info'] == 'already_fahuo':
            wav_name = 'play_dingdanyifahuo.wav'
            wav_url = get_wav_url(wav_name)
            # play_the_wav(wav_url)
            use_mplayer_play_wav(wav_url)  # 使用mplayer播放
            tip['error'] = '该订单已发货'
            return tip


def play_the_wav(wav_url):
    chunk = 1024
    f = wave.open(wav_url, "rb")
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(f.getsampwidth()),
                    channels=f.getnchannels(),
                    rate=f.getframerate(),
                    output=True
                    )
    data = f.readframes(chunk)

    while data != "":
        stream.write(data)
        data = f.readframes(chunk)

    stream.stop_stream()
    stream.close()
    p.terminate()


def use_mplayer_play_wav(wav_url):
    subprocess.call(["mplayer",
                     wav_url],
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)


def get_wav_url(name):
    wav_url = os.path.abspath(os.curdir)+"/addons/hw_scanner/wav_files/"+name
    return wav_url


def start_the_machine(state, scanner_thread):
    # 启动状态机
    print "启动状态机"
    while True:
        if state == 1:  # 初始状态
            state = scanning_so(scanner_thread)
        elif state == 2:
            state = scanning_action(scanner_thread)

        time.sleep(0.1)


