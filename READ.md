                                                                                                    
                                                                                                  
     .%=::::-+.    :::#=::.     +-:..:+@    .+-:..:-##   .+=:..:=+.  .:%-::::==    .#+::::-+:       
      #:     .#.      #:       .%.     -   .#.      .-  .#.      :#    #      %:    =-     .#:      
      #:      +-      #:        .-----:    -+           ==        +-   %=--===:     +-      -+      
      #:      #:      #:             .:#:  :#           -+        #:   %:..:+=      +-      ==      
      #:    .==       #:       #=      #:   ==.     :-   ==.    .+=    %.    :#:    +=    .-+       
     -#=---=-:     ---+=---    ===---==:     .==---=-.    :==--==.   :=#=-    .+=  -++---==:        
                                                                                                    
                                                                                      
                 =%#.    -#%: :+#-.  :-%=.   ==-::-+%     :--#+--:     ==-::-=+#                    
                 .#.#.  :#.#   ==      #.   .%      +        +-       #-      :=                    
                 .# :# .# .#   ==      #.    -=---:.         +-      :#                             
                 .#  :##. .#   ==      #.       ..:-+.       +-      :#                             
                 .#   ..  .#   :#     .#    +-      #-       +-       +=      .:                    
                .=%--    -=%-   :=---==.    ++=----=-     ---#+--:     :==-:-==:     
                                 
                                               
                              :=#=---==:     -=---==:   .#---++--=+                                 
                                %     .%.   +=     .+=  .%   +-  .%                                 
                                %::::-+=   =+        #:  :   +-   :                                 
                                %:::::-=-  ==        #:      +-                                     
                                #       %. .#.      -#       +-                                     
                              .-%-::::-=-   .==::::==      ::#+::



DISCORD MUSIC BOT SETUP GUIDE (DJ-BOB)

This guide explains how to create your Discord music bot, obtain the necessary
credentials, configure the bot, and prepare your system to run it properly.

-------------------------------------------------------------------------------

1. CREATE A NEW BOT ON THE DISCORD DEVELOPER PORTAL

1.1 Go to https://discord.com/developers/applications  
1.2 Click "New Application"  
1.3 Name your application (e.g., DJ-BOB) and click "Create"

-------------------------------------------------------------------------------

2. ADD A BOT USER TO YOUR APPLICATION

2.1 In the left sidebar, select "Bot"  
2.2 Click "Add Bot" and confirm with "Yes, do it!"  
2.3 Under "Privileged Gateway Intents", enable:  
    - MESSAGE CONTENT INTENT  
    - (Optional) SERVER MEMBERS INTENT  
2.4 Under "General Bot Settings", ensure:  
    - Public Bot is enabled  
    - "Requires OAuth2 Code Grant" is disabled

(See the included bot-settings.png for reference.)

-------------------------------------------------------------------------------

3. GET YOUR BOT TOKEN AND CLIENT ID

3.1 In the "Bot" section, click "Copy Token" and save it securely  
3.2 In "OAuth2 > General", copy the CLIENT ID  

You will need both values to configure your bot.config file like this:

[discord]
token = YOUR_BOT_TOKEN
client_id = YOUR_CLIENT_ID

-------------------------------------------------------------------------------

4. INVITE YOUR BOT TO YOUR SERVER

Use this URL format to invite the bot:

https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot%20applications.commands&permissions=2213873984

Replace YOUR_CLIENT_ID with your actual client ID from step 3.  
This link grants the bot all required permissions.

-------------------------------------------------------------------------------

5. INSTALL PYTHON DEPENDENCIES AND FFMPEG

5.1 Ensure Python 3.11 or newer is installed on your system.  
5.2 In the bot directory, run:

    pip install -r requirements.txt

5.3 Install FFmpeg (required for music playback):

    python install_ffmpeg.py

This will download FFmpeg and create a folder like
"ffmpeg-7.1.1-essentials_build" alongside the script.  
The bot requires FFmpeg binaries to be present for audio processing.

-------------------------------------------------------------------------------

6. START THE BOT

Make sure your bot.config file is correctly configured.  
Then start the bot by running:

    python startBot.py

Once running, the bot will appear online and respond to slash commands such as /play.  
It will join voice channels and play audio from provided YouTube links.

-------------------------------------------------------------------------------

END OF INSTRUCTIONS
================================================================================
