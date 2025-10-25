#!/usr/bin/env python3
"""
DEX Liquidity and Advanced Analytics Module
Integrates with Uniswap, PancakeSwap, The Graph, and Moralis
"""

import os
import sys
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

import requests
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()


# ========== CONFIGURATION ==========

# API Keys
MORALIS_API_KEY = os.getenv('MORALIS_API_KEY', '')
THEGRAPH_API_KEY = os.getenv('THEGRAPH_API_KEY', '')

# Subgraph URLs
UNISWAP_V2_SUBGRAPH = os.getenv('UNISWAP_V2_SUBGRAPH', 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
UNISWAP_V3_SUBGRAPH = os.getenv('UNISWAP_V3_SUBGRAPH', 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3')
PANCAKESWAP_V2_SUBGRAPH = os.getenv('PANCAKESWAP_V2_SUBGRAPH', 'https://api.thegraph.com/subgraphs/name/pancakeswap/exchange-v2')
SUSHISWAP_SUBGRAPH = os.getenv('SUSHISWAP_SUBGRAPH', 'https://api.thegraph.com/subgraphs/name/sushi-v2/sushiswap-ethereum')

# Feature flags
ENABLE_DEX_LIQUIDITY = os.getenv('ENABLE_DEX_LIQUIDITY', 'true').lower() == 'true'
ENABLE_HOLDER_ANALYTICS = os.getenv('ENABLE_HOLDER_ANALYTICS', 'true').lower() == 'true'
ENABLE_HISTORICAL_ANALYSIS = os.getenv('ENABLE_HISTORICAL_ANALYSIS', 'true').lower() == 'true'
MAX_HISTORICAL_DAYS = int(os.getenv('MAX_HISTORICAL_DAYS', '90'))

# Known liquidity lock contracts
LIQUIDITY_LOCK_CONTRACTS = {
    'ethereum': [
        '0x663A5C229c09b049E36dCc11a9B0d4a8Eb9db214',  # Unicrypt
        '0x71B5759d73262FBb223956913ecF4ecC51057641',  # UNCX (old)
        '0xDba68f07d1b7Ca219f78ae8582C213d975c25cAf',  # UNCX (new)
        '0xC77aab3c6D7dAb46248F3CC3033C856171878BD5',  # Team Finance
    ],
    'bsc': [
        '0x407993575c91ce7643a4d4cCACc9A98c36eE1BBE',  # PinkLock
        '0x7ee058420e5937496F5a2096f04caA7721cF70cc',  # Mudra
    ]
}


# ========== DEX LIQUIDITY ANALYZER ==========

class DEXLiquidityAnalyzer:
    """Analyzes liquidity across multiple DEXes"""

    def __init__(self, contract_address: str, blockchain: str = 'ethereum'):
        self.contract_address = contract_address.lower()
        self.blockchain = blockchain.lower()
        self._cache = {}

    def _graphql_query(self, subgraph_url: str, query: str) -> dict:
        """Execute GraphQL query against The Graph"""
        try:
            headers = {}
            if THEGRAPH_API_KEY:
                headers['Authorization'] = f'Bearer {THEGRAPH_API_KEY}'

            response = requests.post(
                subgraph_url,
                json={'query': query},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"GraphQL query failed: {e}", file=sys.stderr)
            return {'data': None}

    def get_uniswap_v2_liquidity(self) -> dict:
        """Get Uniswap V2 liquidity information"""
        query = f"""
        {{
          pairs(where: {{token0: "{self.contract_address}"}}, first: 5, orderBy: reserveUSD, orderDirection: desc) {{
            id
            token0 {{
              id
              symbol
            }}
            token1 {{
              id
              symbol
            }}
            reserve0
            reserve1
            reserveUSD
            totalSupply
            createdAtTimestamp
            liquidityProviderCount
          }}
          pairsAlt: pairs(where: {{token1: "{self.contract_address}"}}, first: 5, orderBy: reserveUSD, orderDirection: desc) {{
            id
            token0 {{
              id
              symbol
            }}
            token1 {{
              id
              symbol
            }}
            reserve0
            reserve1
            reserveUSD
            totalSupply
            createdAtTimestamp
            liquidityProviderCount
          }}
        }}
        """

        data = self._graphql_query(UNISWAP_V2_SUBGRAPH, query)

        if not data.get('data'):
            return {}

        # Combine both queries
        all_pairs = (data['data'].get('pairs', []) + data['data'].get('pairsAlt', []))

        if not all_pairs:
            return {}

        # Get largest pool
        largest_pool = max(all_pairs, key=lambda p: float(p.get('reserveUSD', 0)))

        return {
            'dex': 'uniswap_v2',
            'pool_address': largest_pool['id'],
            'token0': largest_pool['token0']['symbol'],
            'token1': largest_pool['token1']['symbol'],
            'reserve_usd': float(largest_pool.get('reserveUSD', 0)),
            'lp_token_supply': float(largest_pool.get('totalSupply', 0)),
            'lp_count': int(largest_pool.get('liquidityProviderCount', 0)),
            'created_timestamp': int(largest_pool.get('createdAtTimestamp', 0)),
            'total_pools': len(all_pairs)
        }

    def get_pancakeswap_liquidity(self) -> dict:
        """Get PancakeSwap liquidity information"""
        if self.blockchain != 'bsc':
            return {}

        query = f"""
        {{
          pairs(where: {{token0: "{self.contract_address}"}}, first: 5, orderBy: reserveUSD, orderDirection: desc) {{
            id
            token0 {{
              id
              symbol
            }}
            token1 {{
              id
              symbol
            }}
            reserve0
            reserve1
            reserveUSD
            totalSupply
            createdAtTimestamp
          }}
          pairsAlt: pairs(where: {{token1: "{self.contract_address}"}}, first: 5, orderBy: reserveUSD, orderDirection: desc) {{
            id
            token0 {{
              id
              symbol
            }}
            token1 {{
              id
              symbol
            }}
            reserve0
            reserve1
            reserveUSD
            totalSupply
            createdAtTimestamp
          }}
        }}
        """

        data = self._graphql_query(PANCAKESWAP_V2_SUBGRAPH, query)

        if not data.get('data'):
            return {}

        all_pairs = (data['data'].get('pairs', []) + data['data'].get('pairsAlt', []))

        if not all_pairs:
            return {}

        largest_pool = max(all_pairs, key=lambda p: float(p.get('reserveUSD', 0)))

        return {
            'dex': 'pancakeswap',
            'pool_address': largest_pool['id'],
            'reserve_usd': float(largest_pool.get('reserveUSD', 0)),
            'lp_token_supply': float(largest_pool.get('totalSupply', 0)),
            'created_timestamp': int(largest_pool.get('createdAtTimestamp', 0)),
            'total_pools': len(all_pairs)
        }

    def check_liquidity_locks(self, pool_address: str, w3: Web3) -> dict:
        """Check if liquidity is locked in known lock contracts"""
        # ERC20 balanceOf ABI
        erc20_abi = [{
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }]

        try:
            lp_contract = w3.eth.contract(
                address=Web3.to_checksum_address(pool_address),
                abi=erc20_abi
            )

            total_locked = 0
            total_supply = lp_contract.functions.totalSupply().call() if hasattr(lp_contract.functions, 'totalSupply') else 0

            lock_contracts = LIQUIDITY_LOCK_CONTRACTS.get(self.blockchain, [])

            for lock_addr in lock_contracts:
                try:
                    balance = lp_contract.functions.balanceOf(Web3.to_checksum_address(lock_addr)).call()
                    total_locked += balance
                except:
                    continue

            locked_percentage = total_locked / total_supply if total_supply > 0 else 0

            return {
                'is_locked': locked_percentage > 0.01,  # >1% locked
                'locked_percentage': locked_percentage,
                'total_locked': total_locked,
                'total_supply': total_supply
            }
        except Exception as e:
            print(f"Failed to check liquidity locks: {e}", file=sys.stderr)
            return {'is_locked': 0, 'locked_percentage': 0}

    def analyze_all_dexes(self, w3: Web3) -> dict:
        """Analyze liquidity across all relevant DEXes"""
        liquidity_data = {}

        # Uniswap V2 (Ethereum/Polygon)
        if self.blockchain in ['ethereum', 'polygon']:
            uniswap_data = self.get_uniswap_v2_liquidity()
            if uniswap_data:
                liquidity_data['uniswap_v2'] = uniswap_data

        # PancakeSwap (BSC)
        if self.blockchain == 'bsc':
            pancake_data = self.get_pancakeswap_liquidity()
            if pancake_data:
                liquidity_data['pancakeswap'] = pancake_data

        # Get largest pool
        if not liquidity_data:
            return {}

        largest_dex = max(
            liquidity_data.values(),
            key=lambda d: d.get('reserve_usd', 0)
        )

        # Check if liquidity is locked
        lock_info = self.check_liquidity_locks(largest_dex['pool_address'], w3)

        return {
            'largest_pool': largest_dex,
            'total_dexes': len(liquidity_data),
            'all_pools': liquidity_data,
            'liquidity_lock': lock_info
        }


# ========== HOLDER ANALYTICS ==========

class HolderAnalytics:
    """Advanced holder distribution analysis using Moralis API"""

    def __init__(self, contract_address: str, blockchain: str = 'ethereum'):
        self.contract_address = contract_address
        self.blockchain = blockchain
        self.api_key = MORALIS_API_KEY

        # Chain mapping for Moralis
        self.chain_map = {
            'ethereum': 'eth',
            'bsc': 'bsc',
            'polygon': 'polygon'
        }

    def get_token_holders(self, limit: int = 500) -> List[dict]:
        """Get token holders from Moralis API"""
        if not self.api_key:
            print("Warning: MORALIS_API_KEY not set, skipping holder analytics", file=sys.stderr)
            return []

        chain = self.chain_map.get(self.blockchain, 'eth')

        try:
            url = f"https://deep-index.moralis.io/api/v2/erc20/{self.contract_address}/owners"

            headers = {
                'X-API-Key': self.api_key,
                'accept': 'application/json'
            }

            params = {
                'chain': chain,
                'limit': limit
            }

            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            return data.get('result', [])

        except Exception as e:
            print(f"Failed to fetch holders from Moralis: {e}", file=sys.stderr)
            return []

    def calculate_gini_coefficient(self, balances: List[float]) -> float:
        """
        Calculate Gini coefficient for token distribution
        0 = perfect equality, 1 = perfect inequality
        """
        if not balances or len(balances) < 2:
            return 0.0

        # Sort balances
        sorted_balances = sorted(balances)
        n = len(sorted_balances)
        cumsum = 0
        sum_balances = sum(sorted_balances)

        if sum_balances == 0:
            return 0.0

        for i, balance in enumerate(sorted_balances):
            cumsum += balance * (n - i)

        gini = (2 * cumsum) / (n * sum_balances) - (n + 1) / n

        return max(0.0, min(1.0, gini))

    def analyze_holder_distribution(self) -> dict:
        """Comprehensive holder distribution analysis"""
        holders = self.get_token_holders(limit=500)

        if not holders:
            return {
                'total_holders': 0,
                'gini_coefficient': 0,
                'top_10_percentage': 0,
                'whale_count': 0,
                'concentration_risk': 'unknown'
            }

        # Extract balances
        balances = []
        for holder in holders:
            try:
                balance = int(holder.get('balance', 0))
                balances.append(balance)
            except:
                continue

        if not balances:
            return {
                'total_holders': len(holders),
                'gini_coefficient': 0,
                'top_10_percentage': 0,
                'whale_count': 0
            }

        total_supply = sum(balances)
        sorted_balances = sorted(balances, reverse=True)

        # Top 10 holders percentage
        top_10_balance = sum(sorted_balances[:10]) if len(sorted_balances) >= 10 else sum(sorted_balances)
        top_10_percentage = top_10_balance / total_supply if total_supply > 0 else 0

        # Count whales (holders with >1% of supply)
        whale_threshold = total_supply * 0.01
        whale_count = sum(1 for b in balances if b > whale_threshold)

        # Gini coefficient
        gini = self.calculate_gini_coefficient(balances)

        # Concentration risk assessment
        if gini > 0.9 or top_10_percentage > 0.9:
            risk = 'extreme'
        elif gini > 0.7 or top_10_percentage > 0.7:
            risk = 'high'
        elif gini > 0.5 or top_10_percentage > 0.5:
            risk = 'moderate'
        else:
            risk = 'low'

        return {
            'total_holders': len(holders),
            'gini_coefficient': gini,
            'top_10_percentage': top_10_percentage,
            'whale_count': whale_count,
            'concentration_risk': risk,
            'largest_holder_percentage': sorted_balances[0] / total_supply if sorted_balances and total_supply > 0 else 0
        }


# ========== HISTORICAL ANALYSIS ==========

class HistoricalAnalyzer:
    """Analyze historical ownership changes and transfer patterns"""

    def __init__(self, contract_address: str, blockchain: str, w3: Web3):
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.blockchain = blockchain
        self.w3 = w3

    def get_transfer_events(self, from_block: int, to_block: int = None) -> List[dict]:
        """Get ERC20 Transfer events from blockchain"""
        # Transfer event signature
        transfer_topic = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

        try:
            if to_block is None:
                to_block = self.w3.eth.block_number

            # Limit range to avoid timeout
            block_range = min(to_block - from_block, 10000)

            logs = self.w3.eth.get_logs({
                'address': self.contract_address,
                'fromBlock': from_block,
                'toBlock': from_block + block_range,
                'topics': [transfer_topic]
            })

            transfers = []
            for log in logs:
                try:
                    # Decode transfer event
                    from_addr = '0x' + log['topics'][1].hex()[26:]
                    to_addr = '0x' + log['topics'][2].hex()[26:]
                    value = int(log['data'].hex(), 16)

                    # Get block timestamp
                    block = self.w3.eth.get_block(log['blockNumber'])

                    transfers.append({
                        'from': from_addr.lower(),
                        'to': to_addr.lower(),
                        'value': value,
                        'block': log['blockNumber'],
                        'timestamp': block['timestamp'],
                        'tx_hash': log['transactionHash'].hex()
                    })
                except Exception as e:
                    continue

            return transfers

        except Exception as e:
            print(f"Failed to get transfer events: {e}", file=sys.stderr)
            return []

    def analyze_ownership_changes(self, days: int = 30) -> dict:
        """Analyze ownership transfer patterns over time"""
        try:
            current_block = self.w3.eth.block_number

            # Estimate blocks per day (assuming ~13s block time for Ethereum)
            blocks_per_day = 6500
            from_block = max(0, current_block - (days * blocks_per_day))

            transfers = self.get_transfer_events(from_block, current_block)

            if not transfers:
                return {
                    'ownership_changes': 0,
                    'suspicious_patterns': 0,
                    'large_transfers': 0
                }

            # Analyze patterns
            ownership_changes = 0
            large_transfers = 0
            transfer_volumes = []

            for transfer in transfers:
                transfer_volumes.append(transfer['value'])

                # Count large transfers (you might want to adjust threshold)
                if transfer['value'] > 0:  # Placeholder
                    large_transfers += 1

                # Detect ownership changes (transfers from owner)
                # This is simplified - would need to track owner address
                ownership_changes += 1

            # Detect suspicious patterns
            # - Many transfers to same address
            # - Large volume spikes
            # - Transfers right after deployment

            recipient_counts = defaultdict(int)
            for transfer in transfers:
                recipient_counts[transfer['to']] += 1

            max_transfers_to_one_addr = max(recipient_counts.values()) if recipient_counts else 0
            suspicious = max_transfers_to_one_addr > len(transfers) * 0.5  # >50% to one address

            # Calculate transfer velocity
            if transfers:
                time_range = transfers[-1]['timestamp'] - transfers[0]['timestamp']
                velocity = len(transfers) / (time_range / 86400) if time_range > 0 else 0
            else:
                velocity = 0

            return {
                'total_transfers': len(transfers),
                'ownership_changes': ownership_changes,
                'large_transfers': large_transfers,
                'suspicious_patterns': suspicious,
                'transfer_velocity': velocity,
                'unique_recipients': len(recipient_counts),
                'max_transfers_to_single_address': max_transfers_to_one_addr
            }

        except Exception as e:
            print(f"Failed to analyze ownership changes: {e}", file=sys.stderr)
            return {
                'ownership_changes': 0,
                'suspicious_patterns': 0
            }


# ========== INTEGRATION HELPERS ==========

def extract_advanced_features(contract_address: str, blockchain: str, w3: Web3) -> dict:
    """
    Extract all advanced features (DEX liquidity, holder analytics, historical)
    This is the main entry point for the advanced analytics
    """
    features = {}

    # ===== DEX LIQUIDITY ANALYSIS =====
    if ENABLE_DEX_LIQUIDITY:
        print("Analyzing DEX liquidity...", file=sys.stderr)
        dex_analyzer = DEXLiquidityAnalyzer(contract_address, blockchain)
        liquidity_data = dex_analyzer.analyze_all_dexes(w3)

        if liquidity_data and liquidity_data.get('largest_pool'):
            pool = liquidity_data['largest_pool']
            lock_info = liquidity_data.get('liquidity_lock', {})

            features['hasLiquidityLock'] = 1 if lock_info.get('is_locked') else 0
            features['liquidityPoolSize'] = pool.get('reserve_usd', 0)
            features['liquidityRatio'] = lock_info.get('locked_percentage', 0)
            features['hasUniswapV2'] = 1 if pool.get('dex') == 'uniswap_v2' else 0
            features['hasPancakeSwap'] = 1 if pool.get('dex') == 'pancakeswap' else 0
            features['multiplePoolsExist'] = 1 if liquidity_data.get('total_dexes', 0) > 1 else 0

            # Pool age
            if pool.get('created_timestamp'):
                pool_age_days = (time.time() - pool['created_timestamp']) / 86400
                features['poolCreatedRecently'] = 1 if pool_age_days < 7 else 0
                features['liquidityLockedDays'] = pool_age_days if lock_info.get('is_locked') else 0
            else:
                features['poolCreatedRecently'] = 0
                features['liquidityLockedDays'] = 0

            # Low liquidity warning
            features['lowLiquidityWarning'] = 1 if pool.get('reserve_usd', 0) < 10000 else 0

            # LP provider concentration
            lp_count = pool.get('lp_count', 0)
            if lp_count > 0:
                # Estimate if owner is major LP (simplified)
                features['liquidityProvidedByOwner'] = 0.5  # Would need more analysis
            else:
                features['liquidityProvidedByOwner'] = 0

            features['rugpullHistoryOnDEX'] = 0  # Would need historical database
            features['slippageTooHigh'] = 0  # Would need to simulate swaps

    # ===== HOLDER ANALYTICS =====
    if ENABLE_HOLDER_ANALYTICS and MORALIS_API_KEY:
        print("Analyzing holder distribution...", file=sys.stderr)
        holder_analyzer = HolderAnalytics(contract_address, blockchain)
        holder_data = holder_analyzer.analyze_holder_distribution()

        if holder_data:
            features['holderCount'] = holder_data.get('total_holders', 0)
            features['holderConcentration'] = holder_data.get('gini_coefficient', 0)
            features['top10HoldersPercent'] = holder_data.get('top_10_percentage', 0)
            features['whaleCount'] = holder_data.get('whale_count', 0)
            features['suspiciousHolderPatterns'] = 1 if holder_data.get('concentration_risk') in ['high', 'extreme'] else 0

    # ===== HISTORICAL ANALYSIS =====
    if ENABLE_HISTORICAL_ANALYSIS:
        print("Analyzing historical transfer patterns...", file=sys.stderr)
        historical_analyzer = HistoricalAnalyzer(contract_address, blockchain, w3)
        historical_data = historical_analyzer.analyze_ownership_changes(days=MAX_HISTORICAL_DAYS)

        if historical_data:
            features['ownershipChangedRecently'] = 1 if historical_data.get('ownership_changes', 0) > 5 else 0
            features['suspiciousPatterns'] = 1 if historical_data.get('suspicious_patterns') else 0
            features['transactionVelocity'] = min(1.0, historical_data.get('transfer_velocity', 0) / 100)

    return features


if __name__ == '__main__':
    # Test the module
    if len(sys.argv) < 2:
        print("Usage: python dex_analytics.py <contract_address> [blockchain]")
        sys.exit(1)

    contract_addr = sys.argv[1]
    blockchain = sys.argv[2] if len(sys.argv) > 2 else 'ethereum'

    # Initialize Web3
    from extract_features import BLOCKCHAIN_CONFIGS
    config = BLOCKCHAIN_CONFIGS.get(blockchain)
    w3 = Web3(Web3.HTTPProvider(config['rpc_url']))

    print(f"Analyzing {contract_addr} on {blockchain}...")
    features = extract_advanced_features(contract_addr, blockchain, w3)

    import json
    print(json.dumps(features, indent=2))
