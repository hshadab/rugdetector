#!/usr/bin/env python3
"""
Batch Feature Extraction Script
Extracts 60 blockchain features from a list of contract addresses
"""

import json
import os
import sys
import time
import subprocess
import pandas as pd
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class BatchFeatureExtractor:
    """Extract features from multiple contracts in parallel"""

    def __init__(self, input_csv: str, output_csv: str = None, max_workers: int = 4):
        self.input_csv = Path(input_csv)
        self.output_csv = Path(output_csv) if output_csv else self.input_csv.parent / "features_extracted.csv"
        self.max_workers = max_workers

        # Feature extraction script
        self.extract_script = Path(__file__).parent.parent / "model" / "extract_features.py"

        if not self.extract_script.exists():
            raise FileNotFoundError(f"Feature extraction script not found: {self.extract_script}")

        print("=" * 70)
        print("Batch Feature Extraction")
        print("=" * 70)
        print(f"Input CSV: {self.input_csv}")
        print(f"Output CSV: {self.output_csv}")
        print(f"Max workers: {self.max_workers}")
        print(f"Extraction script: {self.extract_script}")

    def extract_features_for_contract(self, address: str, blockchain: str, timeout: int = 60) -> Dict:
        """
        Extract features for a single contract

        Args:
            address: Contract address
            blockchain: Blockchain name (ethereum, bsc, polygon, base)
            timeout: Timeout in seconds

        Returns:
            Dict with 60 features or None if extraction failed
        """
        try:
            # Run the feature extraction script
            cmd = [sys.executable, str(self.extract_script), address, blockchain]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                # Parse JSON output
                output = result.stdout.strip()
                features = json.loads(output)
                return features
            else:
                print(f"  ✗ {address} ({blockchain}): {result.stderr[:100]}")
                return None

        except subprocess.TimeoutExpired:
            print(f"  ✗ {address} ({blockchain}): Timeout after {timeout}s")
            return None
        except json.JSONDecodeError as e:
            print(f"  ✗ {address} ({blockchain}): Invalid JSON - {e}")
            return None
        except Exception as e:
            print(f"  ✗ {address} ({blockchain}): {e}")
            return None

    def process_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process a batch of contracts to extract features

        Args:
            df: DataFrame with columns: address, blockchain, label

        Returns:
            DataFrame with features + metadata
        """
        results = []
        total = len(df)

        print(f"\nExtracting features for {total} contracts...")
        print(f"This may take a while (~{total * 30 / 60:.1f} minutes estimated)\n")

        start_time = time.time()
        successful = 0
        failed = 0

        # Process in batches with progress tracking
        for idx, row in df.iterrows():
            address = row['address']
            blockchain = row['blockchain']
            label = row['label']

            print(f"[{idx + 1}/{total}] Processing {address} ({blockchain})...")

            features = self.extract_features_for_contract(address, blockchain)

            if features:
                # Combine features with metadata
                result = {
                    'address': address,
                    'blockchain': blockchain,
                    'label': label,
                    'name': row.get('name', 'Unknown'),
                    'source': row.get('source', 'unknown'),
                    **features  # Merge all 60 features
                }
                results.append(result)
                successful += 1
                print(f"  ✓ Success ({successful}/{total})")
            else:
                failed += 1
                print(f"  ✗ Failed ({failed}/{total})")

            # Progress update every 10 contracts
            if (idx + 1) % 10 == 0:
                elapsed = time.time() - start_time
                rate = (idx + 1) / elapsed
                remaining = (total - idx - 1) / rate if rate > 0 else 0
                print(f"\n  Progress: {idx + 1}/{total} ({100 * (idx + 1) / total:.1f}%)")
                print(f"  Success rate: {100 * successful / (idx + 1):.1f}%")
                print(f"  Time elapsed: {elapsed / 60:.1f} min")
                print(f"  Time remaining: {remaining / 60:.1f} min\n")

        # Create results DataFrame
        results_df = pd.DataFrame(results)

        print("\n" + "=" * 70)
        print("Extraction Summary")
        print("=" * 70)
        print(f"Total contracts: {total}")
        print(f"Successful: {successful} ({100 * successful / total:.1f}%)")
        print(f"Failed: {failed} ({100 * failed / total:.1f}%)")
        print(f"Total time: {(time.time() - start_time) / 60:.1f} minutes")

        return results_df

    def validate_features(self, df: pd.DataFrame) -> bool:
        """
        Validate that all required features are present

        Args:
            df: DataFrame with extracted features

        Returns:
            True if valid, False otherwise
        """
        # Expected 60 features
        expected_features = [
            'hasOwnershipTransfer', 'hasRenounceOwnership', 'ownerBalance', 'ownerTransactionCount',
            'multipleOwners', 'ownershipChangedRecently', 'ownerContractAge', 'ownerIsContract',
            'ownerBlacklisted', 'ownerVerified',
            'hasLiquidityLock', 'liquidityPoolSize', 'liquidityRatio', 'hasUniswapV2',
            'hasPancakeSwap', 'liquidityLockedDays', 'liquidityProvidedByOwner', 'multiplePoolsExist',
            'poolCreatedRecently', 'lowLiquidityWarning', 'rugpullHistoryOnDEX', 'slippageTooHigh',
            'holderCount', 'holderConcentration', 'top10HoldersPercent', 'averageHoldingTime',
            'suspiciousHolderPatterns', 'whaleCount', 'holderGrowthRate', 'dormantHolders',
            'newHoldersSpiking', 'sellingPressure',
            'hasHiddenMint', 'hasPausableTransfers', 'hasBlacklist', 'hasWhitelist',
            'hasTimelocks', 'complexityScore', 'hasProxyPattern', 'isUpgradeable',
            'hasExternalCalls', 'hasSelfDestruct', 'hasDelegateCall', 'hasInlineAssembly',
            'verifiedContract', 'auditedByFirm', 'openSourceCode',
            'avgDailyTransactions', 'transactionVelocity', 'uniqueInteractors', 'suspiciousPatterns',
            'highFailureRate', 'gasOptimized', 'flashloanInteractions', 'frontRunningDetected',
            'contractAge', 'lastActivityDays', 'creationBlock', 'deployedDuringBullMarket',
            'launchFairness'
        ]

        print("\nValidating features...")

        missing_features = []
        for feature in expected_features:
            if feature not in df.columns:
                missing_features.append(feature)

        if missing_features:
            print(f"  ✗ Missing {len(missing_features)} features:")
            for feature in missing_features[:10]:
                print(f"    - {feature}")
            if len(missing_features) > 10:
                print(f"    ... and {len(missing_features) - 10} more")
            return False

        print(f"  ✓ All {len(expected_features)} features present")

        # Check for missing values
        missing_counts = df[expected_features].isnull().sum()
        if missing_counts.sum() > 0:
            print(f"  ⚠ Found missing values in {missing_counts[missing_counts > 0].count()} features")
            print("    These will be filled with 0 during training")

        return True

    def run(self):
        """Execute the batch extraction pipeline"""

        # Load input CSV
        print("\nLoading input data...")
        df = pd.read_csv(self.input_csv)
        print(f"  ✓ Loaded {len(df)} contracts")
        print(f"\nLabel distribution:")
        print(df['label'].value_counts())

        # Process batch
        results_df = self.process_batch(df)

        # Validate features
        if len(results_df) > 0:
            self.validate_features(results_df)

            # Save results
            print(f"\nSaving results to {self.output_csv}...")
            results_df.to_csv(self.output_csv, index=False)
            print(f"  ✓ Saved {len(results_df)} contracts with features")

            # Generate summary
            print("\n" + "=" * 70)
            print("Feature Extraction Complete!")
            print("=" * 70)
            print(f"\nOutput file: {self.output_csv}")
            print(f"Total contracts with features: {len(results_df)}")
            print(f"\nLabel distribution in final dataset:")
            print(results_df['label'].value_counts())
            print(f"\nNext: Run train_model_real.py to train on this data")
        else:
            print("\n✗ No contracts successfully processed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch feature extraction for rug pull detection")
    parser.add_argument("input_csv", help="CSV file with addresses (columns: address, blockchain, label)")
    parser.add_argument("--output", "-o", help="Output CSV file (default: features_extracted.csv)")
    parser.add_argument("--workers", "-w", type=int, default=1, help="Max parallel workers (default: 1)")

    args = parser.parse_args()

    extractor = BatchFeatureExtractor(
        input_csv=args.input_csv,
        output_csv=args.output,
        max_workers=args.workers
    )
    extractor.run()
