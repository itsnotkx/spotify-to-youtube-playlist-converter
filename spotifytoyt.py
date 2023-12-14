from flask import Flask,request, redirect, url_for, session
import requests
import base64
import urllib.parse


#improvements:
#1: client secret, client id, and all sensitive data must be stored in a seperate .env(environment) file, stored locally. to push to github, create a placeholder env file
#   -.env files contain key-value pairs
#2: move error handling and all commonly used functions into a utils module, which stores commonly used fucntions across the program/

client_id="" 
client_secret=""

app=Flask(__name__)

app.secret_key=""
@app.route('/')
def login():
    authdict={
        "scope":"playlist-read-private",
        "client_id": client_id,
        "response_type":"code",
        "redirect_uri":'http://localhost:8888/callback',
        "show_dialog":True
        
    }

    authorization_url="https://accounts.spotify.com/authorize?"
    auth_link = authorization_url + urllib.parse.urlencode(authdict)
    return redirect (auth_link)
    
def access_token_obtain(code):
    data={
        "grant_type":"authorization_code",
        "code":code,
        "redirect_uri":"http://localhost:8888/callback"
    }

    headers={
        'Authorization':"Basic "+base64.b64encode((client_id+":"+client_secret).encode('utf-8')).decode('utf-8'), #dont concatenate and base64 encode like this, will run into errors especially with special characters in the string.

    }

    #base64.b64encode expects input in bytes, so encode(utf-8) converts client_id+':'+client_secret' into bytes
    #after that, as header expects values in string format, the whole output of base64.b64encode is decoded using .decode('utf-8')

    r=requests.post('https://accounts.spotify.com/api/token',headers=headers,data=data)
    if r.status_code == 200:
        token = r.json()["access_token"]
        return token
    else:
        print ("error 2, code  " + str(r.status_code)+","+str(r.json()["error_description"])) #create a new utils module, put all error handling, or in general commonly used functionality throughout the app/
        return "An error has occured"


@app.route("/playlist")
def playlist():
    token = request.args.get('token')
    if token:
        headers={'Authorization':'Bearer '+ token}
        playlists=requests.get('https://api.spotify.com/v1/me/playlists?limit=50',headers=headers)
        if playlists.status_code == 200:
            data=playlists.json()
            a=0
            overall_list=[]
            playlistdata={}
            for i in data["items"]:
                playlist_url_list=data["items"][a]["external_urls"]["spotify"]
                playlist_name_list=data["items"][a]["name"]
                playlist_id_list=data["items"][a]["id"]
                playlistdata[playlist_url_list]=playlist_id_list
                a+=1
                print (playlist_name_list+", URL= "+playlist_url_list)
                overall_list.append(playlist_url_list)
            desired_playlist=input("Select your desired playlist from the items above, by copy pasting the desired playlist link here: ")
            if desired_playlist in overall_list:
                desired_id=playlistdata[desired_playlist]
                return redirect(url_for('extract',desired_id=desired_id,token=token))
            else:
                return ("Error: desired playlist link is incorrect.")
        else:
            print ("error 3, code  " + str(playlists.status_code)+","+str(playlists.json()["error"]))
    else: 
        return "Access token not provided"
    
@app.route("/extract/<desired_id>")
def extract(desired_id):
    token = request.args.get('token')
    if token:
        headers={'Authorization':'Bearer '+ token}
        trackslink="https://api.spotify.com/v1/playlists/"+desired_id+"/tracks"
        songreq=requests.get(trackslink, headers=headers)
        if songreq.status_code==200:
            songjson=songreq.json()
            songlist=[]
            x=0
            for i in songjson["items"]:
                songlist.append(songjson["items"][x]["track"]["name"]+" by "+songjson["items"][x]["track"]["artists"][0]["name"])
                #songlist.append(songjson["items"][x]["track"]["popularity"])
                x+=1
            session["songlist"]=songlist
            print (session)
            return redirect ("/youtubeauth")
        else:
            print("error 4, code " + str(songreq.status_code)+","+str(songreq.json()["error"]))
            return ("not today")
    else:
        return "Error: Access token not provided"

youtube_client_id=""
youtube_client_secret=""

@app.route("/youtubeauth")
def youtubeauth():
    yt_auth_dict={
        "scope":"https://www.googleapis.com/auth/youtube",
        "client_id":youtube_client_id,
        "response_type":"code",
        "redirect_uri":"http://localhost:8888/tokenexchange",
        "prompt":"consent"
    }
    yt_auth_url="https://accounts.google.com/o/oauth2/auth?"+urllib.parse.urlencode(yt_auth_dict)    
    return redirect (yt_auth_url)

@app.route("/tokenexchange")
def tokenexchange():

    ytcode = request.args.get('code')
    if ytcode:
        #obtaining access token for youtube
        print(ytcode)
        params = {
            'code': ytcode,
            'client_id': youtube_client_id,
            'client_secret': youtube_client_secret,
            'redirect_uri': 'http://localhost:8888/tokenexchange',
            'grant_type': 'authorization_code'
            }
        
        yttokenrequest=requests.post('https://oauth2.googleapis.com/token',data=params)
        if yttokenrequest.status_code == 200:
            response=yttokenrequest.json()
            yt_token=response["access_token"]
            return redirect("/createplaylist?token="+yt_token)
        else:
            print ("error 5, code  " + str(yttokenrequest.status_code)+","+str(yttokenrequest.json()["error_description"]))
            return "An error has occured"
    else:
        return ("Authorization code not obtained")

apikey=""
    
@app.route("/createplaylist")
def createplaylist():
    yt_token=request.args.get("token")
    playlisttitle=input("Enter desired title for playlist here: ")
    params={
        "part":"snippet",
        "key":apikey
    }
    data={
        "snippet":{"title":playlisttitle}
    }
    headers={
        "Authorization":"Bearer "+yt_token
    }
    print (data)
    endpoint="https://www.googleapis.com/youtube/v3/playlists?"
    createplaylistrequest=requests.post(url=endpoint,json=data,headers=headers,params=params)
    if createplaylistrequest.status_code==200:
        session["playlistid"]=createplaylistrequest.json()["id"]
        return redirect ("/songfinder?token="+yt_token)
    else:
        return createplaylistrequest.json()
    
@app.route("/songfinder")
def songfinder():
    videoidlist=[]
    yt_token=request.args.get("token")
    list1=session["songlist"]
    for song in list1:
        params={
            "q":song,
            "part":"snippet",
            "maxResults":1,
            "key":apikey,
            "type":"video",
        }

        headers={
            "Authorization":"Bearer "+yt_token
        }
        r=requests.get("https://www.googleapis.com/youtube/v3/search",params=params, headers=headers)
        response=r.json()
        if response:
            videoid = response['items'][0]['id']['videoId']
            videoidlist.append(videoid)
            session["videoidlist"]=videoidlist
    return redirect("/updateplaylist?token="+yt_token)

@app.route("/updateplaylist")
def updateplaylist():
    yt_token=request.args.get("token")
    videoidlist=session["videoidlist"]
    i=0
    for item in videoidlist:
        params={
            "part":"snippet"
        }
        headers={
            "Authorization":"Bearer "+yt_token,
            "key":apikey
        }
        data={
            "snippet":{"playlistId":str(session["playlistid"]),
                    "resourceId":{
                        "videoId":item,
                        "kind":"youtube#video"}
                    }
        }

        r=requests.post("https://www.googleapis.com/youtube/v3/playlistItems",json=data,params=params,headers=headers)
        if r.status_code==200:
            print ("Song added successfully")
        else:
            print(r.json())
        i+=1

    return redirect("https://www.youtube.com/playlist?list="+str(session["playlistid"]))
        

@app.route("/callback")
def callback():
    code = request.args.get('code')
    if code:
        token=access_token_obtain(code)
        if token:
            return redirect("/playlist?token="+token)
        else:
            return "Failed to obtain access token"
    #if token and code:
        #return redirect
    return "No code parameter provided"

if __name__=="__main__":
    app.run('localhost', 8888)
