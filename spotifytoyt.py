from flask import Flask,request, redirect, url_for, session
import requests
import base64
import urllib.parse
from dotenv import load_dotenv
import os
import configparser


#improvements:
#2: move error handling and all commonly used functions into a utils module, which stores commonly used fucntions across the program/
#store parameters and values that tell the program how to run inside a config folder
#figure out how to properly accept inputs
#3.create a SERVER SIDE session with redis and flask


load_dotenv()


config=configparser.ConfigParser()


app=Flask(__name__)


app.secret_key=os.getenv("session_secret_key")


config.read("config.ini")


@app.route('/')
def login(): 
    spotify_client_id=os.getenv("spotify_client_id")
    authdict={
        "scope":config["spotifyauth"]["scope"],
        "client_id":spotify_client_id,
        "response_type":config["spotifyauth"]["response_type"],
        "redirect_uri":config["spotifyauth"]["redirect_uri"],
        "show_dialog":config["spotifyauth"]["show_dialog"],
    }
    authorization_url=config["spotifyauth"]["authorization_url"]
    auth_link = authorization_url + urllib.parse.urlencode(authdict)
    return redirect (auth_link)


@app.route("/callback")
def callback():
    session["code"] = request.args.get('code')
    if session["code"] is not None:
        return redirect ("/spotify_access_token_exchange")


@app.route("/spotify_access_token_exchange")
def access_token_obtain():
    spotify_client_id=os.getenv("spotify_client_id") #dont store this into variables
    spotify_client_secret=os.getenv("spotify_client_secret")
    data={
        "grant_type":config["spotifycodeexchange"]["grant_type"],
        "code":session["code"],
        "redirect_uri":config["spotifycodeexchange"]["redirect_uri"] #reminder: redirect uri for EXCHANGING ACCESS TOKEN FOR CODE and AUTHORIZATION has to be the SAME
        }
    headers={
        'Authorization':"Basic "+base64.b64encode((spotify_client_id+":"+spotify_client_secret).encode('utf-8')).decode('utf-8')
        #change this to properly concatenate it
        }
    r=requests.post('https://accounts.spotify.com/api/token',headers=headers,data=data)
    if r.status_code == 200:
        session["spotify_access_token"] = r.json()["access_token"]
        return redirect ("/playlist")
    else:
        print ("error 2, code  " + str(r.status_code)+","+str(r.json()["error_description"]))
        return "An error has occured"


@app.route("/playlist")
def playlist():
    if session["spotify_access_token"] is not None:
        headers={'Authorization':'Bearer '+ session["spotify_access_token"]}
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

            #add html here and buttons so that no user will copy paste link wrongly

            if desired_playlist in overall_list:
                session["desired_id"]=playlistdata[desired_playlist]
                return redirect(url_for('extract',desired_id=session["desired_id"],token=session["spotify_access_token"]))
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
                x+=1
            session["songlist"]=songlist
            print (session)
            return redirect ("/youtubeauth")
        else:
            print("error 4, code " + str(songreq.status_code)+","+str(songreq.json()["error"]))
            return ("not today")
    else:
        return "Error: Access token not provided"


@app.route("/youtubeauth")
def youtubeauth():
    youtube_client_id=os.getenv("youtube_client_id")
    yt_auth_dict={
        "scope":config["youtubeauth"]["scope"],
        "client_id":youtube_client_id,
        "response_type":config["youtubeauth"]["response_type"],
        "redirect_uri":config["youtubeauth"]["redirect_uri"],
        "prompt":config["youtubeauth"]["prompt"]
    }
    yt_auth_url="https://accounts.google.com/o/oauth2/auth?"+urllib.parse.urlencode(yt_auth_dict)    
    return redirect (yt_auth_url)


@app.route("/tokenexchange")
def tokenexchange():
    youtube_client_id=os.getenv("youtube_client_id")
    youtube_client_secret=os.getenv("youtube_client_secret")
    session["yt_access_code"] = request.args.get('code')
    if session["yt_access_code"] is not None:
        params = {
            'code': session["yt_access_code"],
            'client_id': youtube_client_id,
            'client_secret': youtube_client_secret,
            'redirect_uri': config["youtubeCodeExchange"]["redirect_uri"],
            'grant_type': config["youtubeCodeExchange"]["grant_type"]
            }
        yttokenrequest=requests.post('https://oauth2.googleapis.com/token',data=params)
        if yttokenrequest.status_code == 200:
            session["yt_token"]=yttokenrequest.json()["access_token"]
            #yt_token=response["access_token"]
            return redirect("/createplaylist?token="+session['yt_token'])
        else:
            print ("error 5, code  " + str(yttokenrequest.status_code)+","+str(yttokenrequest.json()["error_description"]))
            return "An error has occured"
    else:
        return ("Authorization code not obtained")


@app.route("/createplaylist")
def createplaylist():
    playlisttitle=input("Enter desired title for playlist here: ")
    params={
        "part":"snippet",
        "key":os.getenv("google_api_key")
        }
    data={
        "snippet":{"title":playlisttitle}
        }
    headers={
        "Authorization":"Bearer "+session["yt_token"]
        }
    print (data)
    endpoint="https://www.googleapis.com/youtube/v3/playlists?"
    createplaylistrequest=requests.post(url=endpoint,json=data,headers=headers,params=params)
    if createplaylistrequest.status_code==200:
        session["playlistid"]=createplaylistrequest.json()["id"]
        return redirect ("/songfinder?token="+session["yt_token"])
    else:
        return createplaylistrequest.json()
    

@app.route("/songfinder")
def songfinder():
    videoidlist=[]
    list1=session["songlist"]
    for song in list1:
        params={
            "q":song,
            "part":"snippet",
            "maxResults":1,
            "key":os.getenv("google_api_key"),
            "type":"video",
        }
        headers={
            "Authorization":"Bearer "+session["yt_token"]
        }
        r=requests.get("https://www.googleapis.com/youtube/v3/search",params=params, headers=headers)
        response=r.json()
        if response:
            videoid = response['items'][0]['id']['videoId']
            videoidlist.append(videoid)
            session["videoidlist"]=videoidlist
    return redirect("/updateplaylist?token="+session["yt_token"])


@app.route("/updateplaylist")
def updateplaylist():
    videoidlist=session["videoidlist"]
    i=0
    for item in videoidlist:
        params={
            "part":"snippet"
        }
        headers={
            "Authorization":"Bearer "+session["yt_token"],
            "key":os.getenv("google_api_key")
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
        

if __name__=="__main__":
    app.run('localhost', 8888)
