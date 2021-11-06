# -*- coding: utf-8 -*-
#------------------------
# v2021-11-01   1.W06, DB + web api
#               2. plot chart
# v2021-11-02   1. TODO: 加入 https://startbootstrap.com/themes 中的範本
#                   ex1: https://startbootstrap.com/theme/business-casual
#                   ex2: https://startbootstrap.com/theme/sb-admin-2
#========================

from flask import Flask, request, abort, render_template, Response
from flask import json, jsonify, session, redirect, url_for
#from flask_cors import CORS, cross_origin # for cross domain problem
from flask import send_file

import requests
import csv
import folium
import geocoder

from apscheduler.schedulers.background import BackgroundScheduler
import os

from sqlalchemy import create_engine
import time, datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

IS_LOCAL = 0

app = Flask(__name__, static_url_path='', static_folder='static')

@app.route("/", methods=['GET'])
def basic_url():
    return 'hello'

@app.route("/hello", methods=['GET'])
def hello():
    name = request.args.get('name')
    return 'hello ' + name

@app.route("/map/kh-parking", methods=['GET'])
def map_kh_parking():
    url = "https://data.kcg.gov.tw/dataset/449e45d9-dead-4873-95a9-cc34dabbb3af/resource/fe3f93da-9673-4f7b-859c-9017d793f798/download/108.6.21.csv"
    r = requests.get(url)
    print(r)
    decoded_content = r.content.decode('utf-8')
    cr = csv.reader(decoded_content.splitlines(), delimiter=',')
    data_list = list(cr)

    # 開始產生地圖
    location = geocoder.osm('高雄市').latlng
    m = folium.Map(location=location, zoom_start=14)
    for item in data_list[1:]:
        try:
            name = item[2]
            total = item[7]
            fee = item[10]
            lat = item[5]
            lng = item[4]
            info = '%s<br>%s<br>停車格數：%s' %(name, fee, total)
            
            folium.Marker([float(lat), float(lng)], tooltip=info,
                        icon=folium.Icon(color='green', prefix='fa', icon='fa-car')).add_to(m)
            
        except Exception as e:
            print(e.args)    
            
    m.save('./map_kh_parking.html')

    return send_file('./map_kh_parking.html')


@app.route("/map/w01-6", methods=['GET'])
def map_w01_6():
    return app.send_static_file('W01-6.html')

#-- W06 DB + web api
@app.route('/aqi/data', methods=['GET'])
def aqi_data():
    sid = request.args.get('sid')
    if not sid:
        return jsonify({'result':'NG', 'log':'sid miss'})

    mysql_db_url = 'mysql+pymysql://user1:ji3g4user1@206.189.86.205:32769/testdb'
    my_db = create_engine(mysql_db_url)
    resultProxy=my_db.execute("select * from malo_1030_aqi_table2 where uuid='%s' ORDER BY time ASC" %(sid) )
    data = resultProxy.fetchall()

    my_data_list = list()
    for item in data:
        my_data_list.append( dict(item) )

    result = {'result':'OK', 'data':my_data_list}
    return jsonify(result)

@app.route('/aqi/data/24h', methods=['GET'])
def aqi_data_24h():
    sid = request.args.get('sid')
    if not sid:
        return jsonify({'result':'NG', 'log':'sid miss'})
    
    dt2 = datetime.datetime.now()
    dt1 = dt2-datetime.timedelta(days=1)
    tm_start = dt1.strftime("%Y/%m/%d %H:%M:%S")
    tm_end = dt2.strftime("%Y/%m/%d %H:%M:%S")
    
    mysql_db_url = 'mysql+pymysql://user1:ji3g4user1@206.189.86.205:32769/testdb'
    my_db = create_engine(mysql_db_url)
    sql_cmd = "select * from malo_1030_aqi_table2 where uuid='%s' and time>'%s' and time<='%s' ORDER BY time ASC" %(sid, tm_start, tm_end)
    print(sql_cmd)
    resultProxy=my_db.execute( sql_cmd )
    data = resultProxy.fetchall()

    my_data_list = list()
    for item in data:
        my_data_list.append( dict(item) )

    result = {'result':'OK', 'data':my_data_list}
    return jsonify(result)

#-- TODO: 更適合前端畫圖的API格式

@app.route('/aqi/chart/24h', methods=['GET'])
def aqi_chart_24h():
    sid = request.args.get('sid')
    if not sid:
        return jsonify({'result':'NG', 'log':'sid miss'})
    
    dt2 = datetime.datetime.now()
    dt1 = dt2-datetime.timedelta(days=1)
    tm_start = dt1.strftime("%Y/%m/%d %H:%M:%S")
    tm_end = dt2.strftime("%Y/%m/%d %H:%M:%S")
    
    mysql_db_url = 'mysql+pymysql://user1:ji3g4user1@206.189.86.205:32769/testdb'
    my_db = create_engine(mysql_db_url)
    sql_cmd = "select * from malo_1030_aqi_table2 where uuid='%s' and time>'%s' and time<='%s' ORDER BY time ASC" %(sid, tm_start, tm_end)
    print(sql_cmd)
    resultProxy=my_db.execute( sql_cmd )
    data = resultProxy.fetchall()

    aqi_list = list()
    for item in data:
        aqi_list.append( float(item['aqi']) )

    # plot
    plt.plot(aqi_list)
    plt.grid()
    plt.savefig('img.png')
    plt.close()
    return send_file('img.png', mimetype='image/png')

#####################
# Scheduler
#####################
def job_wakeup():
    print('cron fun1: awake myself')
    url = 'https://malo-cron2.herokuapp.com/'
    r = requests.get(url)
    print(r)

def send_line(msg, token='rpHUQIIMkArQh6EtQpqfjK6hjPN2jjNxh0zDbcFVoD2'):
    url = "https://notify-api.line.me/api/notify"  # --> 不支援http, 只能用https
    headers = {"Authorization" : "Bearer "+ token}
    title = '排程測試'
    message =  '[%s] %s' %(title, msg)
    payload = {"message" :  message}

    r = requests.post(url ,headers = headers ,params=payload)
    
#- 空污通報
def job_function2():
    url = 'https://data.epa.gov.tw/api/v1/aqx_p_432?format=json&api_key=9be7b239-557b-4c10-9775-78cadfc555e9'
    r = requests.get(url)
    print(r)
    data = r.json()
    records = data['records']
    for item in records:
        if item['County']=='高雄市' and item['SiteName']=='鳳山':
            send_line('%s>> AQI=%s' %(item['SiteName'], item['AQI']))

#- 空污資料收集
def job_function3():
    mysql_db_url = 'mysql+pymysql://user1:ji3g4user1@206.189.86.205:32769/testdb'
    my_db = create_engine(mysql_db_url)

    # check and create table
    resultProxy = my_db.execute("CREATE TABLE IF NOT EXISTS your_table (uuid text NOT NULL, time text NOT NULL, aqi text, pm25 text)")

    # get data
    url = 'https://data.epa.gov.tw/api/v1/aqx_p_432?format=json&api_key=9be7b239-557b-4c10-9775-78cadfc555e9'
    r = requests.get(url)
    data = r.json()
    records = data['records']
    uuid = ''
    my_time = ''
    aqi = ''
    pm25 = ''
    for item in records:
        if item['County']=='高雄市':
            uuid = item['SiteName']
            my_time = item['PublishTime']
            aqi = item['AQI']
            pm25 = item['PM2.5']

            # insert
            resultProxy=my_db.execute("insert into your_table (uuid, time, aqi, pm25) values('%s', '%s', '%s', '%s')" %(uuid, my_time, aqi, pm25))

    # get data from db
    resultProxy=my_db.execute("select * from your_table")
    data = resultProxy.fetchall()
    print('-- data --')
    print(data)

def start_scheduler():
    scheduler = BackgroundScheduler()

    # run every 10 minute
    scheduler.add_job(job_wakeup, 'cron', minute='*/10')

    # 每天早上6:30執行
    scheduler.add_job(job_function2, 'cron', hour='6', minute='30')
    #scheduler.add_job(job_function2, 'cron', minute='*/1')

    # 每小時的20分執行
    #scheduler.add_job(job_function3, 'cron', minute='20')

    # start the scheduler
    scheduler.start()

def run_web():
    os.system('gunicorn -w 2 app:app')

if __name__ == "__main__":
    
    if IS_LOCAL:
        app.run(debug=True)
    else:
        start_scheduler()
        run_web()
