# monsta-slurper
Buy limit order script for https://app.cake.monster/ $MONSTA token

!WINDOWS ONLY FOR NOW!

Instructions:
1. Download "Monsta Slurper Program.rar"
2. Unzip anywhere on your computer
3. Edit config.json to include your private key* for the wallet you want to trade MONSTA on.
4. Run "slurp.exe"
5. SLURP THAT DIP!

*NOTE: No one will be able to see or access your private key in the config.json



GUI Explained:
1. Displays current price of $MONSTA, automatically refreshes two times per second.
2. Enter the target price to buy $MONSTA at. (If you put a price higher than current price it will buy immediately)
3. How much BNB to use for the purchase.
4. How much Gas price to use in GWEI. (Gas limit is hard coded to 400,000 to reduce failures)
5. How many times to retry purchase if it fails. (If the transactions fails on the chain it will use gas every retry)
6. Click "Run" to start the program, while running it will wait for the dip and buy.
7. Click "Stop" to stop the program, if you want to change values it can not be running.
8. Click "Exit" to close the program.

![monstagui](https://user-images.githubusercontent.com/90290113/138597137-983177e3-6b74-47ca-9675-85cbdd72b63b.png)
