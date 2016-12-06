#coding:utf-8

from openerp import http
from openerp.addons.web.controllers.main import ensure_db
from openerp.http import request
from openerp.addons.hw_scanner.controllers.picking import get_info, update_info
import requests
import json


def update_server_password(data):

    tip = {}
    headers = {'Content-TYpe': 'application/json'}
    url = data['server_ip']+":8069/app_api/session/authenticate"
    request_data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {'login': data['username'], 'password': data['old_password']}
    }
    s = requests.session()
    try:
        res = s.post(url, data=json.dumps(request_data), headers=headers).json()
        if res and 'session_id' in res['result']:
            url_update = data['server_ip'] + ":8069/app_api/session/change_password"
            request_update_data = {
                "jsonrpc": "2.0",
                "method": "call",
                'params': {"old_password": data['old_password'],
                           "new_password": data['new_password']}
            }
            update_res = s.post(url_update, data=json.dumps(request_update_data), headers=headers).json()
            if update_res and 'msg' in update_res['result']:
                tip['msg'] = update_res['result']['msg']
            else:
                tip['error'] = res['result']['error']
        else:
            tip['error'] = '登录服务器失败'
    except Exception:
        tip['error'] = ' 网络连接失败或服务器错误'
    return tip


class RevicePassword(http.Controller):
    @http.route('/revice_password', type='http', auth='none')
    def revice_password(self,redirect=None,**kwargs):
        ensure_db()
        result = {}
        userinfo = get_info()
        result['server_ip'] = userinfo['server_ip']
        if request.httprequest.method == 'POST':
            if userinfo:
                right_old_password = userinfo['password']  # 获得正确的原密码
            old_password = request.params['old_password1']
            new_password1 = request.params['new_password1']
            new_password2 = request.params['new_password2']
            server_ip = request.params['server_ip']
            if old_password and new_password1 and new_password2 and server_ip:
                if new_password1 == new_password2:
                    if old_password == right_old_password:  # 验证正确
                        # 服务器修改
                        send_data = {}
                        send_data['username'] = userinfo['username']
                        send_data['old_password'] = right_old_password
                        send_data['new_password'] = new_password1
                        send_data['server_ip'] = server_ip
                        try:
                            tip = update_server_password(send_data)  # 更新服务器password
                            if 'error' in tip:
                                result['msg'] = tip['error']
                            elif 'msg' in tip:
                                # 本地修改
                                values = {}
                                values['new_password'] = new_password1
                                values['server_ip'] = server_ip
                                update_info(values)
                                result['msg'] = tip['msg']
                            else:
                                result['msg'] = '更新密码失败'
                        except Exception:
                            result['msg'] = '网络连接失败或服务器错误'
                    else:
                        result['msg'] = '原密码错误'
                else:
                    result['msg'] = '两次新密码不相同'
            else:
                    result['msg'] = '所有数据都不能为空'
        return request.render('revice_password.revice_password', result)
