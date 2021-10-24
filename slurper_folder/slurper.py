from web3 import Web3
from eth_account import Account
import json
import os
import datetime
from time import sleep
import traceback
import PySimpleGUI as sg


class SlurperClass:
    def __init__(self, monsta_address):
        # Load config file and ABI's
        filepath = os.path.realpath(os.getcwd())
        print("You can minimize this window but not close it.")
        configFile = filepath + "\\config.json"
        pcsABI = filepath + "\\psc_abi.json"
        balanceABI = filepath + "\\balance_abi.json"

        with open(configFile) as f:
            self.config = json.load(f)
        with open(pcsABI) as f:
            self.pcs_abi = json.load(f)
        with open(balanceABI) as f:
            self.balance_check_abi = json.load(f)

        # Connect to RPC
        self.rpc_url = self.config["RPC"]
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        # Pancakeswap Router Contract
        self.pcs_address = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
        self.pcs_contract = self.w3.eth.contract(
            address=self.pcs_address, abi=self.pcs_abi)

        # MONSTA token properly formatted for web3
        self.monsta_token = Web3.toChecksumAddress(monsta_address)

        # Read wallet private key
        self.account = Account.from_key(self.config["PRIVATE_KEY"])

        # Chain ID of BSC mainnet
        self.chainId = "0x38"

        # Wrapped BNB address
        self.bnb_address = Web3.toChecksumAddress(
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")

        # USDC address
        self.usdc_address = Web3.toChecksumAddress(
            "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d")

        self.gasLimit = 400000

    def get_monsta_price_in_usdc(self):
        # Use 1 BNB to base USDC and MONSTA amountsOut
        amount_in = Web3.toWei(1, 'ether')

        # Get current price of BNB in USDC
        usdc_out = self.pcs_contract.functions.getAmountsOut(
            amount_in, [self.bnb_address, self.usdc_address]).call()[1]
        usdc_out = Web3.fromWei(usdc_out, 'ether')

        # Get current price of MONSTA in BNB
        amountsOut = self.pcs_contract.functions.getAmountsOut(
            amount_in, [self.bnb_address, self.monsta_token]).call()[1]
        amountsOut = Web3.fromWei(amountsOut, 'ether')

        # Calculate MONSTA price in USDC
        real_price = float(usdc_out) / float(amountsOut)

        # Convert to readable format
        formatted_price = ("{:0.18f}".format(real_price))

        return formatted_price

    def get_monsta_balance(self):
        # Load balance check contract
        balance_check_contract = self.w3.eth.contract(
            address=self.monsta_token, abi=self.balance_check_abi)

        # Get amount of MONSTA held in wallet and convert to readable format
        balance = balance_check_contract.functions.balanceOf(self.account.address).call({'from': self.monsta_token})
        token_amount = Web3.fromWei(balance, 'ether')
        tokens_owned = ("{:0.18f}".format(token_amount))

        return tokens_owned

    def get_bnb_balance(self, convertToBNB=True):
        # Get amount of BNB held in wallet
        balance = self.w3.eth.getBalance(self.account.address)
        if convertToBNB:
            return Web3.fromWei(balance, 'ether')
        return balance

    def swapExactETHForTokensSupportingFeeOnTransferTokens(self, transferAmountInBNB, gasPriceGwei=8,
                                                           max_slippage=5, minutesDeadline=5, actually_send_trade=False,
                                                           retries=1, verbose=False):
        # Convert BNB to BNB-Wei
        transferAmount = Web3.toWei(transferAmountInBNB, "ether")
        # Get BNB balance
        balance = self.get_bnb_balance(False)

        if verbose:
            print(
                f"Balance before send: {balance} MATIC\n------------------------")

        if balance < transferAmount:
            raise Exception(
                "Requested swap value is greater than the account balance. Will not execute this trade.")

        # Find the expected output amount of MONSTA with slippage
        amountsOut = self.pcs_contract.functions.getAmountsOut(
            transferAmount, [self.bnb_address, self.monsta_token]).call()[1]
        amountOutMin = (100 - max_slippage) / 100 * amountsOut

        # Arbitrary deadline, can tighten to reject transactions that takes too long
        deadline = datetime.datetime.now(
            datetime.timezone.utc).timestamp() + (minutesDeadline * 60)

        # Fill ABI data payload with parameters:
        # swapExactETHForTokens(uint256 amountOutMin, address[] path, address to, uint256 deadline)
        swap_abi = self.pcs_contract.encodeABI('swapExactETHForTokens',
                                                     args=[int(amountOutMin), [self.bnb_address, self.monsta_token],
                                                           self.account.address, int(deadline)])

        """
        <DANGER -- ACTUALLY EXECUTE THE SWAP>
        """
        if actually_send_trade:
            for i in range(retries):
                try:
                    # Fill in ABI and remaining transaction details
                    rawTransaction = {
                        "from": self.account.address,
                        "to": self.pcs_address,
                        "nonce": Web3.toHex(self.w3.eth.getTransactionCount(self.account.address)),
                        "gasPrice": Web3.toHex(int(gasPriceGwei * 1e9)),
                        "gas": Web3.toHex(self.gasLimit),
                        "data": swap_abi,
                        "chainId": self.chainId,
                        "value": Web3.toHex(transferAmount)
                    }

                    if verbose:
                        print(
                            f"Raw of Transaction: \n${rawTransaction}\n------------------------")

                    # Sign the transaction
                    signedTx = self.w3.eth.account.sign_transaction(
                        rawTransaction, self.config["PRIVATE_KEY"])

                    # Send the signed transaction
                    deploy_txn = self.w3.eth.send_raw_transaction(
                        signedTx.rawTransaction)

                    # Get the transaction receipt
                    txn_receipt = self.w3.eth.wait_for_transaction_receipt(deploy_txn, timeout=240)
                    if verbose:
                        print("TXN Receipt:\n", txn_receipt)

                    # Check status of txn_receipt
                    if not txn_receipt["status"] == 1:
                        raise Exception("Transaction failed on the blockchain")

                    return txn_receipt

                # Retry if transaction fails
                except Exception as e:
                    traceback.print_exc()
                    print(e)
                    print(f"Failed on attempt {i + 1}/{retries}")
                    sleep(0.5)
        """
            </DANGER>
        """

        return "Failed"

    def load_gui(self):
        sg.change_look_and_feel('Dark Blue 3')

        # Set the layout for GUI
        layout = [[sg.Text('SLURP THAT DIP!')],
                  [sg.Text('Current $MONSTA price:'), sg.Text(key='-MONSTAPRICE-', font='Courier 8')],
                  [sg.Text('Price to buy at:', size=(14, 1)), sg.In(k='-PRICE-', size=(10, 1))],
                  [sg.Text('BNB to spend:', size=(14, 1)), sg.In('0.0001', k='-BNB-', size=(10, 1)),
                            sg.Text('Available BNB: '+str("{:0.9f}".format(self.get_bnb_balance(True))))],
                  [sg.Text('Gas price (GWEI):', size=(14, 1)), sg.In('5', k='-GAS-', size=(10, 1))],
                  [sg.Text('Retries:', size=(14, 1)), sg.In('2', k='-RETRY-', size=(10, 1))],
                  [sg.Text('', key='-BOUGHT-')],
                  [sg.Button('Run', key='-RUN-'), sg.Button('Stop')],
                  [sg.Button('Exit')]]

        # Set GUI window with layout
        window = sg.Window('MONSTA SLURPER', layout)

        # Ugly way of determining if Run button has been pressed or not lol
        count = 0

        while True:
            # Timeout = refresh rate of window
            event, values = window.read(timeout=500)

            # Get current MONSTA price and continuously update in window
            monsta_price = "{:0.18f}".format(float(self.get_monsta_price_in_usdc()))
            window['-MONSTAPRICE-'].update(f'$' + monsta_price)

            # Exit button closes program
            if event in (None, 'Exit'):
                break

            # Stop button stops it from running buy function
            if event in (None, 'Stop'):
                window['-RUN-'].update('Run', disabled=False)
                window['-PRICE-'].update(disabled=False)
                window['-BNB-'].update(disabled=False)
                window['-GAS-'].update(disabled=False)
                window['-RETRY-'].update(disabled=False)
                count = 0

            # Run button waits for MONSTA to dip lower than target price
            elif event == '-RUN-':
                window['-RUN-'].update('Running', disabled=True)
                window['-PRICE-'].update(disabled=True)
                window['-BNB-'].update(disabled=True)
                window['-GAS-'].update(disabled=True)
                window['-RETRY-'].update(disabled=True)
                count = 1

            # If the MONSTA price goes lower than target and Run button is pressed, execute purchase transaction
            if monsta_price < (values['-PRICE-']) and count == 1:
                window['-BOUGHT-'].update('Triggered buy at $'+monsta_price)
                self.swapExactETHForTokensSupportingFeeOnTransferTokens(
                    (float(values['-BNB-'])), (int(values['-GAS-'])), 6, 1, True, int(values['-RETRY-']), True)
                count += 1