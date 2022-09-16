import pyodbc
import os
import re
from typing import Callable
from slack_bolt import App, Say, BoltContext
from slack_sdk import WebClient
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient
import datetime
import jaconv
import json
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

keyVaultName = os.environ["KEY_VAULT_NAME"]
KVUri = f"https://{keyVaultName}.vault.azure.net"

credential = DefaultAzureCredential()
client = SecretClient(vault_url=KVUri, credential=credential)

server = 'sql-sbx-tama.database.windows.net'
database = 'tama'
username = 'tamasbx'
azure_sql_password =client.get_secret("tamaSql-Pass")
print(azure_sql_password)
password = '{'+str(azure_sql_password.value)+'}'   
print(password)
driver= '{ODBC Driver 17 for SQL Server}'
conn = pyodbc.connect('DRIVER='+driver+';SERVER=tcp:'+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)
conn.autocommit = True
cursor = conn.cursor()
updatecursor = conn.cursor()
insertcursor = conn.cursor()

ASK_CHANNEL_ID = "C041K90RKJA"
LOGGER_CHANNEL_ID = "C041K90RKJA"
SLACK_BOT_TOKEN = client.get_secret("SLACK-BOT-TOKEN-test").value
SLACK_SIGNING_SECRET = client.get_secret("TEST-SLACK-SECRET").value
SLACK_APP_TOKEN = client.get_secret("SLACK-APP-TOKEN-test").value
channelid ="C041K90RKJA"
# ボットトークンと署名シークレットを使ってアプリを初期化します
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

@app.command("/tama")
def open_modal(ack, body, client):
    # Acknowledge the command request
        ack()
        param = body['text']
        if param == 'create':
                # Call views_open with the built-in client
                client.views_open(
                trigger_id=body["trigger_id"],
                # Pass a valid trigger_id within 3 seconds of receiving it
                view ={
                      "callback_id": "tamacreate",
                      "title": {
                          "type": "plain_text",
                          "text": "たま用語追加"
                                },
                      "submit": {
                          "type": "plain_text",
                          "text": "Submit"
                      },
                      "blocks": [
                             {
                              "type": "input",
                              "element": {
                                  "type": "plain_text_input",
                                  "action_id": "term",
                                  "placeholder": {
                                      "type": "plain_text",
                                      "text": "追加したい用語"
                                                 },
                                      "multiline": True,
                                         },
                              "label": {
                                  "type": "plain_text",
                                  "text": "用語"
                                       }
                              },
                             {
                              "type": "input",
                              "element": {
                                  "type": "plain_text_input",
                                  "action_id": "explanation",
                                  "placeholder": {
                                      "type": "plain_text",
                                      "text": "追加したい用語の説明"
                                                 },
                                                 "multiline": True,
                                         },
                              "label": {
                                  "type": "plain_text",
                                  "text": "説明"
                              }
                          }
                      ],
                      "type": "modal"
                  }
             )
        elif param == 'update':
                client.views_open(
                trigger_id=body["trigger_id"],
                # Pass a valid trigger_id within 3 seconds of receiving it
           view = {
                     "callback_id": "tamaupdate",
                     "title": {
                         "type": "plain_text",
                         "text": "上書き学習するにゃ"
                               },
                     "submit": {
                         "type": "plain_text",
                         "text": "Submit"
                     },
                        "blocks": [
                            {
                                "type": "input",
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "term",
                                    "placeholder": {
                                        "type": "plain_text",
                                        "text": "更新したい用語。"
                                    },
                                "multiline": True,
                                },
                                "label": {
                                    "type": "plain_text",
                                    "text": "用語"
                                }
                                },
                            {
                                "type": "input",
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "explanation",
                                    "placeholder": {
                                        "type": "plain_text",
                                        "text": "更新したい用語の説明"
                                    },
                                "multiline": True,
                                },
                                "label": {
                                    "type": "plain_text",
                                    "text": "説明"
                                }
                                }
                            ],
                        "type": "modal"
                        }
                )
                
@app.view("tamaupdate")
def view_submission(ack, body, logger,say, client):
    ack()
    userid = body["user"]["id"]
    termAndExplain = list(body["view"]["state"]["values"].values())
    NEW_WORD = list(termAndExplain[0]["term"].values())[1]
    NEW_EXPLAIN = list(termAndExplain[1]["explanation"].values())[1]
    
    query: str = NEW_WORD.lower()
    query = jaconv.hira2kata(query)
    query = jaconv.h2z(query)
    
    Selection: List[str] = []
    res_text: List[str] = []
    sqlterm : List[str] = []
    
    sqldata = cursor.execute("SELECT * FROM tama")
    row = cursor.fetchone()
    while row:
            print(str(row[1]))
            sqlterm.append(str(row[1]))
            row = cursor.fetchone()

    #入力値のValidationをかける。存在しているか？複数あるか？
    stripped = list(map(str.rstrip, sqlterm))
    
    for k in stripped:
        
        target: str = k.lower()
        target = jaconv.hira2kata(target)
        target = jaconv.h2z(target)
        
        if (len(query) >= 2 and query in target) or query == target:
           Selection.append(k)
           #Explanation.append(k[1])
           title = ",".join(k.split("\n"))
           res_text.append(f"*{title}*\n")
          # res_text.append(f"*{title}*\n{k2[1]}\n")
          # リストを文字列に変換
           res_text1 = "".join(res_text)
           
    if len(Selection) >= 2:
          # 複数の選択があることを伝える。
           say(f"候補が複数あるにゃ。今回は完全一致があれば更新するにゃ。更新されない場合には対象を明確にしてもう一回 `/tama update` でおしえてにゃ。", channel=channelid)
           say(res_text1, channel=channelid)
           
    elif len(Selection) == 0:
           say(f"これ実はたまが知らない単語にゃ。 `/tama create` で教えてニャ。", channel=channelid)
           return
    
    #対象用語を検索して上書きする。
    for i in stripped:
        target: str = i.lower()
        target = jaconv.hira2kata(target)
        target = jaconv.h2z(target)
        print(target)
        print(query)
        
        if query == target:
            updatecursor.execute(f"UPDATE tama SET explanation = N'{NEW_EXPLAIN}' WHERE term = N'{NEW_WORD}'")
            updatecursor.commit()
            say(f"上書き学習したにゃ。 `@tama` で確認できるにゃ。", channel=channelid)
            say(f"<@{userid}> が{NEW_WORD}を{NEW_EXPLAIN} で更新してくれたニャ。", channel=channelid)
            print(f"UPDATE tama SET explanation = N'{NEW_EXPLAIN}' WHERE term = N'{NEW_WORD}'")
        

                   
@app.view("tamacreate")
def view_submission(ack, body, logger, say, message):
    ack()
    userid = body["user"]["id"]
    termAndExplain = list(body["view"]["state"]["values"].values())
    
    NEW_WORD = list(termAndExplain[0]["term"].values())[1]
    NEW_EXPLAIN = list(termAndExplain[1]["explanation"].values())[1]
    
    query: str = NEW_WORD.lower()
    query = jaconv.hira2kata(query)
    query = jaconv.h2z(query)
    
    #NEW_WORDを使って該当する言葉を検索。
    Selection: List[str] = []
    res_text: List[str] = []
    sqlterm : List[str] = []
    
    sqldata = cursor.execute("SELECT * FROM tama")
    row = cursor.fetchone()
    
    while row:
            print(str(row[1]))
            sqlterm.append(str(row[1]))
            row = cursor.fetchone()

    #入力値のValidationをかける。存在しているか？複数あるか？
    stripped = list(map(str.rstrip, sqlterm))
    for k in stripped:
        
        target: str = k.lower()
        target = jaconv.hira2kata(target)
        target = jaconv.h2z(target)
        
        if target == query:
           text = f"<@{userid}> ありがとうにゃ。でもこの用語はしってるにゃ。 `/tama update` で新しい意味をおしえてにゃ。"
           say(text, channel=channelid)
           return
           
    insertcursor.execute(f"INSERT INTO tama VALUES(1, N'{NEW_WORD}', N'{NEW_EXPLAIN}');")
    insertcursor.commit()
    say(f"教えてくれてありがとうございますにゃ。学習したにゃ。 `@tama` で確認できるにゃ。", channel=channelid)
    say(f"<@{userid}> が{NEW_WORD}を{NEW_EXPLAIN} で登録してくれたニャ。", channel=channelid)
    
@app.event("app_mention")
def message_search(body, say,message):
    try:
         # Dict、リストに入った問い合わせ内容ををBodyから抜き出す
         elementvalues2 = body['event']['blocks'][0]['elements'][0]['elements']
         userid = body['event']['user']
         channelid = body['event']['channel']

         # thread_tsをBodyから抜き出す。
         thread_ts = body['event'].get("thread_ts", None) or body['event']['ts']

         #空白だったら”わかんにゃい”
         try:
             text = elementvalues2[1]
         except IndexError as e:
             say(f"わかんにゃい", thread_ts=thread_ts)
             exit()

         orquery = text['text']
         # Dictに入った値をBodyから抜き出して単語のみにする
         text_str = json.dumps(orquery, ensure_ascii=False).strip('"')
         text_str2 = text_str.strip()

         # helpがきたら使い方解説入れる予定
         if text_str2 == 'help' or "":
             say(f"知りたい用語を教えてほしいニャン！ `@たま 用語` で答えるニャン。 用語集の管理は <用語集> ここで管理しているニャン。どんどん追加して欲しいニャン。", thread_ts=thread_ts)
             return

                 # 英数字は小文字に統一
                 # ひらがなは全角カタカナに統一
         query: str = text_str2.lower()
         query = jaconv.hira2kata(query)
         query = jaconv.h2z(query)

         # 空白のリストを用意（たまからのメッセージ入れ物）
         res_text: List[str] = []
         row: List[str] = []

         #NEW_WORDを使って該当する言葉を検索。
         Selection: List[str] = []
         res_text: List[str] = []
         sqlterm : List[str] = []
         sqlexpl : List[str] = []
         stripped : List[str] = []
    
         sqldata = cursor.execute("SELECT * FROM tama")
         row = cursor.fetchone()
    
         while row:
            sqlterm.append(str(row[1]))
            sqlexpl.append(str(row[2]))
            row = cursor.fetchone()

          #入力値のValidationをかける。存在しているか？複数あるか？
         strippedterm: List[str] = list(map(str.rstrip, sqlterm))
         strippedexpl: List[str] = list(map(str.rstrip, sqlexpl))

               
         for c in list(zip(strippedterm, strippedexpl)):
              print(c)
              target: str = c[0].lower()
              target = jaconv.hira2kata(target)
              target = jaconv.h2z(target)
              print(target)
             # 検索結果がもしも空白だった場合にはbreak
              if target == "":
                 break

             # もしも検索結果が2文字以上でターゲットに類似、もしくは同じだった場合
              elif (len(query) >= 2 and query in target) or query == target:

             # ","で分割して改行で分割、res_textに解説をAppendする
                     title = ",".join(c[0].split("\n"))
                     res_text.append(f"*{title}*\n{c[1]}\n")
                     print(res_text)
             # リストを文字列に変換
                     res_text1 = "".join(res_text[-1])

             # たまが答える
                     say(res_text1, thread_ts=thread_ts)

         if not res_text:
             print("どうかにゃ？")
             now = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')

             res_text: List[str] = []
             sqluterm : List[str] = []
             sqlunumber : List[str] = []
             stripped : List[str] = []
    
             sqldata = cursor.execute("SELECT * FROM unknown")
             row = cursor.fetchone()
    
             while row:
                sqluterm.append(str(row[0]))
                sqlunumber.append(str(row[1]))
                row = cursor.fetchone()

              #入力値のValidationをかける。存在しているか？複数あるか？
             strippeduterm: List[str] = list(map(str.rstrip, sqluterm))
             strippedunumber: List[str] = list(map(str.rstrip, sqlunumber))

               
             for c in list(zip(strippeduterm, strippedunumber)):
                  print(c)
                  target: str = c[0].lower()
                  target = jaconv.hira2kata(target)
                  target = jaconv.h2z(target)
                  print(target)
             # 検索結果がもしも空白だった場合には新規追加
                  if target == query:
                     print("用語が見つからなかったのでインクリメントします")
                     
                     count = c[1]
                     print(count)
                     if count == "":
                         count = 0
                     else:
                        count = int(count)
                        print(count)
                        count = count + 1
                        print(count)
                        print((f"UPDATE unknown SET numbers = {count}, updated_date = '{now}' WHERE term = N'{text_str2}'"))
                        updatecursor.execute(f"UPDATE unknown SET numbers = {count}, updated_date = '{now}' WHERE term = N'{text_str2}'")
                        updatecursor.commit()
                        break
             else:
                     print("用語が見つからなかったので新規追加します")
                     print(f"INSERT INTO unknown (term, numbers, created_date, updated_date) VALUES(N'{text_str2}', 1, {now}, {now});")
                     insertcursor.execute(f"INSERT INTO unknown (term, numbers, created_date, updated_date) VALUES(N'{text_str2}', 1, '{now}', '{now}');")
                     insertcursor.commit()
                     

             # ログとして #bot_test_tellme に出力する
         if LOGGER_CHANNEL_ID:
            
                 if not res_text:
                     say(f"*{text_str2}*\nでもこの用語は分かんにゃい・・・だれか`/tama create`で <用語集> に追加して欲しいにゃん", thread_ts=thread_ts)
                     
                     text = f"<#{channelid}> で <@{userid}> が *{query}* を検索したにゃ。"
                     say(text, channel=LOGGER_CHANNEL_ID)
    
                 if not res_text and not LOGGER_CHANNEL_ID:
                     say(f"*{text_str2}* \nでもこの用語は分かんにゃい・・・だれか`/tama create`で <用語集> に追加して欲しいにゃん", thread_ts=thread_ts)
                     
    except Exception as E:
     
     say("エラーが発生したニャン・・・", thread_ts=thread_ts)
     say(f"<#{channelid}> で <@{userid}> が *{query}* を検索してエラーがでたにゃん。", channel=LOGGER_CHANNEL_ID)

# アプリを起動します
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
