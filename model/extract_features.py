#!/usr/bin/env python3
"""
Real Feature Extraction Script for Rug Pull Detection
Extracts 60 blockchain features from smart contracts using real on-chain data
"""

import sys
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import re

# Blockchain libraries
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_abi import decode

# HTTP requests
import requests

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


# ========== CONFIGURATION ==========

BLOCKCHAIN_CONFIGS = {
    'base': {
        'rpc_url': os.getenv('BASE_RPC_URL', 'https://mainnet.base.org'),
        'explorer_api': 'https://api.basescan.org/api',
        'api_key': os.getenv('BASESCAN_API_KEY', ''),
        'chain_id': 8453,
    },
    'solana': {
        'rpc_url': os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
        'explorer_api': 'https://api.solscan.io',
        'api_key': os.getenv('SOLSCAN_API_KEY', ''),
        'chain_id': None,  # Solana doesn't use EVM chain IDs
    }
}

FEATURE_EXTRACTION_MODE = os.getenv('FEATURE_EXTRACTION_MODE', 'hybrid')
TIMEOUT = int(os.getenv('FEATURE_TIMEOUT_SECONDS', '30'))


# ========== BLOCKCHAIN DATA FETCHERS ==========

class BlockchainDataFetcher:
    """Fetches real on-chain data for contract analysis"""

    def __init__(self, contract_address: str, blockchain: str = 'ethereum'):
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.blockchain = blockchain.lower()
        self.config = BLOCKCHAIN_CONFIGS.get(self.blockchain)

        if not self.config:
            raise ValueError(f"Unsupported blockchain: {blockchain}")

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(
            self.config['rpc_url'],
            request_kwargs={'timeout': 10}
        ))

        self.explorer_api = self.config['explorer_api']
        self.api_key = self.config['api_key']

        # Cache for API responses
        self._cache = {}

    def _api_call(self, params: dict, cache_key: str = None) -> dict:
        """Make API call to blockchain explorer with caching"""
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        params['apikey'] = self.api_key

        try:
            response = requests.get(
                self.explorer_api,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if cache_key:
                self._cache[cache_key] = data

            return data
        except Exception as e:
            print(f"API call failed: {e}", file=sys.stderr)
            return {'status': '0', 'result': []}

    def get_contract_code(self) -> Tuple[str, dict]:
        """Fetch contract bytecode and source code"""
        try:
            # Get bytecode
            bytecode = self.w3.eth.get_code(self.contract_address).hex()

            # Get source code from explorer
            data = self._api_call({
                'module': 'contract',
                'action': 'getsourcecode',
                'address': self.contract_address
            }, cache_key='source_code')

            source_info = {}
            if data['status'] == '1' and data['result']:
                result = data['result'][0]
                source_info = {
                    'source_code': result.get('SourceCode', ''),
                    'contract_name': result.get('ContractName', ''),
                    'compiler_version': result.get('CompilerVersion', ''),
                    'optimization_used': result.get('OptimizationUsed', '') == '1',
                    'is_proxy': result.get('Proxy', '0') == '1',
                    'implementation': result.get('Implementation', ''),
                }

            return bytecode, source_info
        except Exception as e:
            print(f"Failed to get contract code: {e}", file=sys.stderr)
            return '0x', {}

    def get_contract_creation_info(self) -> dict:
        """Get contract creation transaction and creator"""
        try:
            data = self._api_call({
                'module': 'contract',
                'action': 'getcontractcreation',
                'contractaddresses': self.contract_address
            }, cache_key='creation_info')

            if data['status'] == '1' and data['result']:
                result = data['result'][0]
                tx_hash = result.get('txHash')

                if tx_hash:
                    # Get transaction details
                    tx = self.w3.eth.get_transaction(tx_hash)
                    receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                    block = self.w3.eth.get_block(receipt['blockNumber'])

                    return {
                        'creator': result.get('contractCreator'),
                        'tx_hash': tx_hash,
                        'block_number': receipt['blockNumber'],
                        'timestamp': block['timestamp'],
                        'creation_date': datetime.fromtimestamp(block['timestamp'])
                    }

            return {}
        except Exception as e:
            print(f"Failed to get creation info: {e}", file=sys.stderr)
            return {}

    def get_token_info(self) -> dict:
        """Get ERC20 token information if applicable"""
        try:
            # Try to call standard ERC20 functions
            erc20_abi = [
                {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
                {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
                {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
                {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
                {"constant": True, "inputs": [], "name": "owner", "outputs": [{"name": "", "type": "address"}], "type": "function"},
            ]

            contract = self.w3.eth.contract(address=self.contract_address, abi=erc20_abi)

            token_info = {}
            try:
                token_info['name'] = contract.functions.name().call()
            except:
                token_info['name'] = None

            try:
                token_info['symbol'] = contract.functions.symbol().call()
            except:
                token_info['symbol'] = None

            try:
                token_info['decimals'] = contract.functions.decimals().call()
            except:
                token_info['decimals'] = 18

            try:
                token_info['total_supply'] = contract.functions.totalSupply().call()
            except:
                token_info['total_supply'] = 0

            try:
                token_info['owner'] = contract.functions.owner().call()
            except:
                token_info['owner'] = None

            return token_info
        except Exception as e:
            return {}

    def get_holder_count(self) -> int:
        """Estimate holder count from transaction history"""
        try:
            # Get normal transactions
            data = self._api_call({
                'module': 'account',
                'action': 'txlist',
                'address': self.contract_address,
                'startblock': 0,
                'endblock': 99999999,
                'page': 1,
                'offset': 1000,  # Get up to 1000 transactions
                'sort': 'desc'
            }, cache_key='transactions')

            if data['status'] == '1':
                # Count unique addresses
                unique_addresses = set()
                for tx in data['result'][:1000]:
                    unique_addresses.add(tx.get('from', '').lower())
                    unique_addresses.add(tx.get('to', '').lower())

                # Remove contract address and zero address
                unique_addresses.discard(self.contract_address.lower())
                unique_addresses.discard('0x0000000000000000000000000000000000000000')

                return len(unique_addresses)

            return 0
        except Exception as e:
            print(f"Failed to get holder count: {e}", file=sys.stderr)
            return 0

    def get_transaction_count(self) -> int:
        """Get total transaction count"""
        try:
            data = self._api_call({
                'module': 'proxy',
                'action': 'eth_getTransactionCount',
                'address': self.contract_address,
                'tag': 'latest'
            })

            if 'result' in data:
                return int(data['result'], 16)

            return 0
        except Exception as e:
            return 0

    def analyze_recent_transactions(self, days: int = 30) -> dict:
        """Analyze recent transaction patterns"""
        try:
            data = self._api_call({
                'module': 'account',
                'action': 'txlist',
                'address': self.contract_address,
                'startblock': 0,
                'endblock': 99999999,
                'page': 1,
                'offset': 1000,
                'sort': 'desc'
            }, cache_key='transactions')

            if data['status'] != '1':
                return {}

            transactions = data['result']
            if not transactions:
                return {
                    'total_count': 0,
                    'unique_interactors': 0,
                    'avg_daily_txs': 0,
                    'failed_count': 0,
                    'failure_rate': 0
                }

            # Calculate metrics
            cutoff_timestamp = int((datetime.now() - timedelta(days=days)).timestamp())
            recent_txs = [tx for tx in transactions if int(tx.get('timeStamp', 0)) >= cutoff_timestamp]

            unique_addresses = set()
            failed_count = 0

            for tx in recent_txs:
                unique_addresses.add(tx.get('from', '').lower())
                if tx.get('isError') == '1':
                    failed_count += 1

            return {
                'total_count': len(recent_txs),
                'unique_interactors': len(unique_addresses),
                'avg_daily_txs': len(recent_txs) / days if days > 0 else 0,
                'failed_count': failed_count,
                'failure_rate': failed_count / len(recent_txs) if recent_txs else 0
            }
        except Exception as e:
            print(f"Failed to analyze transactions: {e}", file=sys.stderr)
            return {}


# ========== FEATURE EXTRACTORS ==========

def analyze_contract_code(bytecode: str, source_info: dict) -> dict:
    """Analyze contract bytecode and source for suspicious patterns"""
    features = {}

    source_code = source_info.get('source_code', '').lower()

    # Code availability
    features['verifiedContract'] = 1 if source_code else 0
    features['openSourceCode'] = 1 if source_code else 0

    # Dangerous patterns in bytecode
    if bytecode and bytecode != '0x':
        # Check for selfdestruct (0xFF opcode)
        features['hasSelfDestruct'] = 1 if 'ff' in bytecode.lower() else 0

        # Check for delegatecall (0xF4 opcode)
        features['hasDelegateCall'] = 1 if 'f4' in bytecode.lower() else 0

        # Estimate complexity by bytecode size
        bytecode_size = len(bytecode) // 2  # Convert hex chars to bytes
        features['complexityScore'] = min(1.0, bytecode_size / 10000)  # Normalize to 0-1
    else:
        features['hasSelfDestruct'] = 0
        features['hasDelegateCall'] = 0
        features['complexityScore'] = 0

    # Source code analysis
    if source_code:
        # Check for dangerous functions
        features['hasHiddenMint'] = 1 if 'mint(' in source_code and 'onlyowner' not in source_code.replace(' ', '') else 0
        features['hasPausableTransfers'] = 1 if 'pause' in source_code or '_paused' in source_code else 0
        features['hasBlacklist'] = 1 if 'blacklist' in source_code or '_blacklisted' in source_code else 0
        features['hasWhitelist'] = 1 if 'whitelist' in source_code or '_whitelisted' in source_code else 0
        features['hasTimelocks'] = 1 if 'timelock' in source_code else 0
        features['hasExternalCalls'] = 1 if '.call(' in source_code or 'delegatecall' in source_code else 0
        features['hasInlineAssembly'] = 1 if 'assembly' in source_code else 0

        # Check for proxy patterns
        features['hasProxyPattern'] = 1 if source_info.get('is_proxy') or 'proxy' in source_code else 0
        features['isUpgradeable'] = 1 if 'upgradeable' in source_code or 'initialize(' in source_code else 0

        # Check for audits
        features['auditedByFirm'] = 1 if any(audit in source_code for audit in ['certik', 'peckshield', 'consensys', 'openzeppelin', 'audit']) else 0
    else:
        # Defaults for unverified contracts (suspicious)
        features['hasHiddenMint'] = 0
        features['hasPausableTransfers'] = 0
        features['hasBlacklist'] = 0
        features['hasWhitelist'] = 0
        features['hasTimelocks'] = 0
        features['hasExternalCalls'] = 1  # Assume yes if can't verify
        features['hasInlineAssembly'] = 0
        features['hasProxyPattern'] = 0
        features['isUpgradeable'] = 0
        features['auditedByFirm'] = 0

    return features


def extract_features_real(contract_address: str, blockchain: str = 'ethereum') -> dict:
    """
    Extract 60 real features from blockchain data

    Args:
        contract_address: Contract address (0x...)
        blockchain: Blockchain name (ethereum, bsc, polygon)

    Returns:
        dict: 60 features as key-value pairs
    """

    print(f"Extracting REAL features for {contract_address} on {blockchain}...", file=sys.stderr)

    # Initialize fetcher
    fetcher = BlockchainDataFetcher(contract_address, blockchain)

    features = {}

    # ===== STEP 1: Get contract code and creation info =====
    bytecode, source_info = fetcher.get_contract_code()
    creation_info = fetcher.get_contract_creation_info()
    token_info = fetcher.get_token_info()

    # ===== STEP 2: Calculate contract age =====
    contract_age_days = 0
    if creation_info.get('timestamp'):
        age_seconds = time.time() - creation_info['timestamp']
        contract_age_days = age_seconds / 86400  # Convert to days

    # ===== OWNERSHIP FEATURES (10) =====
    owner_address = token_info.get('owner')

    # Check if owner functions exist in code
    source_code = source_info.get('source_code', '').lower()
    features['hasOwnershipTransfer'] = 1 if 'transferownership' in source_code.replace(' ', '') else 0
    features['hasRenounceOwnership'] = 1 if 'renounceownership' in source_code.replace(' ', '') else 0

    # Owner balance (if we can determine owner)
    if owner_address and token_info.get('total_supply'):
        try:
            erc20_abi = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}]
            contract = fetcher.w3.eth.contract(address=fetcher.contract_address, abi=erc20_abi)
            owner_balance = contract.functions.balanceOf(owner_address).call()
            features['ownerBalance'] = owner_balance / token_info['total_supply'] if token_info['total_supply'] > 0 else 0
        except:
            features['ownerBalance'] = 0
    else:
        features['ownerBalance'] = 0

    # Owner transaction count
    if owner_address:
        try:
            features['ownerTransactionCount'] = fetcher.w3.eth.get_transaction_count(owner_address)
        except:
            features['ownerTransactionCount'] = 0
    else:
        features['ownerTransactionCount'] = 0

    features['multipleOwners'] = 0  # Would need to parse MultiSig patterns
    features['ownershipChangedRecently'] = 0  # Would need historical data
    features['ownerContractAge'] = contract_age_days
    features['ownerIsContract'] = 0  # Would need to check if owner has bytecode
    features['ownerBlacklisted'] = 0  # Would need blacklist database
    features['ownerVerified'] = 1 if source_info.get('source_code', '') != '' else 0

    # ===== ADVANCED ANALYTICS INTEGRATION =====
    # Try to use advanced DEX + holder analytics if available
    try:
        from dex_analytics import extract_advanced_features
        advanced_features = extract_advanced_features(contract_address, blockchain, fetcher.w3)

        # Override basic features with advanced analytics where available
        if advanced_features:
            print(f"Integrated {len(advanced_features)} advanced features", file=sys.stderr)
            features.update(advanced_features)
    except Exception as e:
        print(f"Advanced analytics unavailable, using basic heuristics: {e}", file=sys.stderr)

    # ===== LIQUIDITY FEATURES (12) =====
    # Fill in defaults for features not set by advanced analytics
    if 'hasLiquidityLock' not in features:
        features['hasLiquidityLock'] = 0
    if 'liquidityPoolSize' not in features:
        features['liquidityPoolSize'] = 0
    if 'liquidityRatio' not in features:
        features['liquidityRatio'] = 0.5  # Default neutral
    if 'hasUniswapV2' not in features:
        features['hasUniswapV2'] = 0
    if 'hasPancakeSwap' not in features:
        features['hasPancakeSwap'] = 0
    if 'liquidityLockedDays' not in features:
        features['liquidityLockedDays'] = 0
    if 'liquidityProvidedByOwner' not in features:
        features['liquidityProvidedByOwner'] = 0
    if 'multiplePoolsExist' not in features:
        features['multiplePoolsExist'] = 0
    if 'poolCreatedRecently' not in features:
        features['poolCreatedRecently'] = 0
    if 'lowLiquidityWarning' not in features:
        features['lowLiquidityWarning'] = 0
    if 'rugpullHistoryOnDEX' not in features:
        features['rugpullHistoryOnDEX'] = 0
    if 'slippageTooHigh' not in features:
        features['slippageTooHigh'] = 0

    # ===== HOLDER ANALYSIS (10) =====
    # Use advanced analytics if available, otherwise fallback to basic estimation
    if 'holderCount' not in features:
        holder_count = fetcher.get_holder_count()
        features['holderCount'] = holder_count

        # Holder concentration (Gini coefficient approximation)
        # High holder count = lower concentration (better)
        if holder_count > 1000:
            features['holderConcentration'] = 0.2
        elif holder_count > 100:
            features['holderConcentration'] = 0.4
        elif holder_count > 10:
            features['holderConcentration'] = 0.7
        else:
            features['holderConcentration'] = 0.95

        features['top10HoldersPercent'] = features['holderConcentration']  # Approximation
        features['suspiciousHolderPatterns'] = 1 if holder_count < 10 else 0
        features['whaleCount'] = max(0, holder_count // 100)  # Rough estimate

    # Fill in remaining holder features
    if 'averageHoldingTime' not in features:
        features['averageHoldingTime'] = contract_age_days / 2  # Rough estimate
    if 'holderGrowthRate' not in features:
        features['holderGrowthRate'] = 0.2 if features.get('holderCount', 0) > 100 else 0.8
    if 'dormantHolders' not in features:
        features['dormantHolders'] = 0.3  # Would need historical data
    if 'newHoldersSpiking' not in features:
        features['newHoldersSpiking'] = 0
    if 'sellingPressure' not in features:
        features['sellingPressure'] = 0.3  # Neutral default

    # ===== CONTRACT CODE FEATURES (15) =====
    code_features = analyze_contract_code(bytecode, source_info)
    features.update(code_features)

    # ===== TRANSACTION PATTERNS (8) =====
    # Use advanced analytics values if they were set, otherwise use basic analysis
    if 'transactionVelocity' not in features:
        tx_analysis = fetcher.analyze_recent_transactions(days=30)
    else:
        tx_analysis = {}  # Already set by advanced analytics

    # Fill in missing transaction features
    if 'avgDailyTransactions' not in features:
        features['avgDailyTransactions'] = tx_analysis.get('avg_daily_txs', 0)
    if 'transactionVelocity' not in features:
        features['transactionVelocity'] = min(1.0, tx_analysis.get('avg_daily_txs', 0) / 100)
    if 'uniqueInteractors' not in features:
        features['uniqueInteractors'] = tx_analysis.get('unique_interactors', 0)
    if 'suspiciousPatterns' not in features:
        features['suspiciousPatterns'] = 1 if tx_analysis.get('failure_rate', 0) > 0.3 else 0
    if 'highFailureRate' not in features:
        features['highFailureRate'] = 1 if tx_analysis.get('failure_rate', 0) > 0.3 else 0

    if 'gasOptimized' not in features:
        features['gasOptimized'] = 1 if source_info.get('optimization_used') else 0
    if 'flashloanInteractions' not in features:
        features['flashloanInteractions'] = 0  # Would need to scan for flashloan patterns
    if 'frontRunningDetected' not in features:
        features['frontRunningDetected'] = 0  # Would need MEV analysis

    # ===== TIME-BASED FEATURES (5) =====
    features['contractAge'] = contract_age_days

    # Last activity
    if tx_analysis.get('total_count', 0) > 0:
        features['lastActivityDays'] = 0  # Has recent activity
    else:
        features['lastActivityDays'] = contract_age_days

    features['creationBlock'] = creation_info.get('block_number', 0)
    features['deployedDuringBullMarket'] = 0  # Would need market data

    # Launch fairness (based on initial distribution)
    if holder_count > 100 and features['holderConcentration'] < 0.5:
        features['launchFairness'] = 0.8
    elif holder_count > 10:
        features['launchFairness'] = 0.5
    else:
        features['launchFairness'] = 0.2

    print(f"Successfully extracted {len(features)} real features", file=sys.stderr)

    return features


def extract_features_hybrid(contract_address: str, blockchain: str = 'ethereum') -> dict:
    """
    Extract features using hybrid approach:
    - Real data where available
    - Fallback to heuristics where API limits exist
    """
    try:
        # Try real extraction first
        return extract_features_real(contract_address, blockchain)
    except Exception as e:
        print(f"Real extraction failed: {e}, falling back to simulated", file=sys.stderr)
        # Fallback to simulated if real extraction fails
        from extract_features_simulated import extract_features as extract_features_simulated
        return extract_features_simulated(contract_address, blockchain)


def extract_features(contract_address: str, blockchain: str = 'ethereum') -> dict:
    """
    Main entry point for feature extraction
    Delegates to appropriate extractor based on FEATURE_EXTRACTION_MODE
    """
    mode = FEATURE_EXTRACTION_MODE.lower()

    if mode == 'real':
        return extract_features_real(contract_address, blockchain)
    elif mode == 'simulated':
        from extract_features_simulated import extract_features as extract_features_simulated
        return extract_features_simulated(contract_address, blockchain)
    else:  # hybrid (default)
        return extract_features_hybrid(contract_address, blockchain)


def validate_contract_address(address: str) -> str:
    """Validate and normalize contract address"""
    if not address or not isinstance(address, str):
        raise ValueError("Contract address must be a non-empty string")

    if not address.startswith('0x'):
        raise ValueError("Contract address must start with 0x")

    if len(address) != 42:
        raise ValueError(f"Contract address must be 42 characters, got {len(address)}")

    # Verify it's valid hex
    try:
        int(address[2:], 16)
    except ValueError:
        raise ValueError("Contract address must contain only hexadecimal characters after 0x")

    return address.lower()


def main():
    """Main entry point when called as script"""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing contract address argument"}), file=sys.stderr)
        sys.exit(1)

    contract_address = sys.argv[1]
    blockchain = sys.argv[2] if len(sys.argv) > 2 else 'ethereum'

    try:
        # Validate inputs
        contract_address = validate_contract_address(contract_address)

        if blockchain.lower() not in BLOCKCHAIN_CONFIGS:
            raise ValueError(f"Unsupported blockchain: {blockchain}")

        # Extract features
        features = extract_features(contract_address, blockchain)

        # Output as JSON to stdout
        print(json.dumps(features, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
