from hashlib import sha256
import json
import time
from uuid import uuid4
from urllib.parse import urlparse

from flask import Flask, request, jsonify
import requests
from getmac import get_mac_address as gma

# from Crypto.PublicKey import RSA
# from Crypto.Signature.pkcs1_15 import PKCS115_SigScheme
# from Crypto.Hash import SHA256
# import binascii


class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    #    def clone_transactions_for_leafhash(self):
    #     leafhash=[]
    #     for txn in self.transactions:
    #         print(txn)
    #         txn_string = json.dumps(txn, sort_keys=True)
    #         leafhash.append(compute_Sha256(txn_string.encode()))
    #         # print(leafhash)
    #     return leafhash

    # def compute_merkle_root(self):#calculate the merkle root of the transactions
    #     print("new recurssion")
    #     if len(self.leafhash)!=1:
    #         if len(self.leafhash)%2==0:
    #             j=0
    #             for i in range(0,len(self.leafhash)-1,2):
    #                 hash_string = json.dumps(self.leafhash[i]+self.leafhash[i+1], sort_keys=True)
    #                 self.leafhash[j] = compute_Sha256(hash_string.encode())
    #                 i+=1
    #                 j+=1
    #                 print("i = ",i," j = ",j)
    #             print("self.leafhash = ",self.leafhash)
    #             self.compute_merkle_root()
    #         else:
    #             self.leafhash.append(self.leafhash[len(self.leafhash)-1])
    #             self.compute_merkle_root()
    #     else:
    #         return self.leafhash[0]
        

    def compute_hash(self):
        """
        A function that return the hash of the block contents.
        """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


#{
    # transaction:[]
    #index:5454
    #ts:asfdsafd
    # ph:asfdasfd
    #merkle_hash:sha256(txn)
# }

class Blockchain:
    # difficulty of our PoW algorithm
    difficulty = 2
    maxTxnInBlock = 10

    def __init__(self):
        self.unconfirmed_transactions = []
        self.chain = []

    def create_genesis_block(self):
        """
        A function to generate genesis block and appends it to
        the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        """
        genesis_block = Block(0, [], 0, "0")
        # genesis_block.merkle_hash = genesis_block.compute_merkle_root()
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of latest block
          in the chain match.
        """
        previous_hash = self.last_block.hash

        if previous_hash != block.previous_hash:
            return False

        if not Blockchain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    @staticmethod
    def proof_of_work(block):
        """
        Function that tries different values of nonce to get a hash
        that satisfies our difficulty criteria.
        """
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)
        if len(self.unconfirmed_transactions)%self.maxTxnInBlock==0: #mine the block if it contains more than 10 transactions
            mine_unconfirmed_transactions()
    
    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    @classmethod                                                     #has to be commented out 
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            # remove the hash field to recompute the hash again
            # using `compute_hash` method.
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self):
        """
        This function serves as an interface to add the pending
        transactions to the blockchain by adding them to the block
        and figuring out Proof Of Work.
        """
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.ctime(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_transactions = []

        return True


app = Flask(__name__)

# the node's copy of blockchain
blockchain = Blockchain()
blockchain.create_genesis_block()

# the address to other participating members of the network
peers = set()

@app.route('/time', methods=['GET'])
def gettimeofTxn():
    chain_data = []
    timestamp_arr=[]
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    for item in chain_data:
        timestamp_arr.append(item["timestamp"])
    jsonString = json.dumps(timestamp_arr)
    return jsonString


@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["Customer", "Amount", "Drink"]

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404

    tx_data["timestamp"] = time.ctime()

    blockchain.add_new_transaction(tx_data)

    return "Success", 201


# endpoint to return the node's copy of the chain.
# Our application will be using this endpoint to query
# all the posts to display.
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data,
                       "peers": list(peers)})


# endpoint to request the node to mine the unconfirmed
# transactions (if any). We'll be using it to initiate
# a command to mine from our application itself.
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    else:
        # Making sure we have the longest chain before announcing to the network
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            # announce the recently mined block to the network
            announce_new_block(blockchain.last_block)
        return "Block #{} is mined.".format(blockchain.last_block.index)


# endpoint to add new peers to the network.
@app.route('/register_node', methods=['POST'])
def register_new_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    # Add the node to the peer list
    peers.add(node_address)

    # Return the consensus blockchain to the newly registered node
    # so that he can sync
    return get_chain()


@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to
    register current node with the node specified in the
    request, and sync the blockchain as well as peer data.
    """
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        global peers
        # update chain and the peers
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain


# endpoint to add a block mined by someone else to
# the node's chain. The block is first verified by the node
# and then added to the chain.
@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201


@app.route('/getmac')
#endpoint to get the macaddress of a node
def getmacadd():
    return gma()

# endpoint to query unconfirmed transactions
@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)

@app.route('/connect_node', methods = ['POST'])
def connect_node():
    json = requests.get_json()
    nodes = json.get('nodes')
    
    # return none if node feild is null
    if nodes is None:
        return 'No node', 400
    
    for node in nodes:
        blockchain.add_node(node)

    # give the response for all the connected nodes and display the nodes
    response = {'message' : 'All the nodes are now connected.',
                'total_nodes' : list(blockchain.nodes)}
    
    # http 201 - request has succeeded and has led to the creation of a resource
    return jsonify(response), 201

def consensus():
    """
    Our naive consensus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('{}chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True

    return False


def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for peer in peers:
        url = "{}add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)





# # Digital signatures implementation

# # Generate 1024-bit RSA key pair (private + public key)
# keyPair = RSA.generate(bits=1024)
# pubKey = keyPair.publickey()

# # Sign the message using the PKCS#1 v1.5 signature scheme (RSASP1)
# msg = b'Message for RSA signing'
# hash = SHA256.new(msg)
# signer = PKCS115_SigScheme(keyPair)
# signature = signer.sign(hash)
# print("Signature:", binascii.hexlify(signature))

# # Verify valid PKCS#1 v1.5 signature (RSAVP1)
# msg = b'Message for RSA signing'
# hash = SHA256.new(msg)
# verifier = PKCS115_SigScheme(pubKey)
# try:
#     verifier.verify(hash, signature)
#     print("Signature is valid.")
# except:
#     print("Signature is invalid.")

# # Verify invalid PKCS#1 v1.5 signature (RSAVP1)
# msg = b'A tampered message'
# hash = SHA256.new(msg)
# verifier = PKCS115_SigScheme(pubKey)
# try:
#     verifier.verify(hash, signature)
#     print("Signature is valid.")
# except:
#     print("Signature is invalid.")




# Uncomment this line if you want to specify the port number in the code
app.run(debug=True, port=5002)
print("app running on port :",5002)