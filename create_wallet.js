const { Coinbase, Wallet } = require('@coinbase/coinbase-sdk');

async function createOrGetWallet() {
  try {
    // Configure with your CDP credentials
    Coinbase.configure({
      apiKeyId: '93d8abc8-7555-44e0-a634-aafa4e1b0fb6',
      apiKeySecret: 'tJrg42SpprPI+uMhSRjBpBElJJb0XdmQrqJSa2xqZtKRrusz/xuKjtVxmMTnpRBl8Jh3QKJ1KoNIn6LzxFi3Mw=='
    });

    console.log('Creating wallet on Base network...');
    
    // Create a new wallet on Base
    const wallet = await Wallet.create({ networkId: 'base-mainnet' });
    
    // Get the default address
    const address = await wallet.getDefaultAddress();
    
    console.log('\n✅ Wallet created successfully!');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('Wallet ID:', wallet.getId());
    console.log('Network:', 'Base Mainnet');
    console.log('Address:', address.getId());
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('\n📝 Save this wallet data securely:');
    console.log(JSON.stringify({
      walletId: wallet.getId(),
      address: address.getId(),
      network: 'base-mainnet'
    }, null, 2));
    
    // Export wallet data (you should save this securely)
    const walletData = wallet.export();
    console.log('\n🔐 Wallet seed (SAVE THIS SECURELY):');
    console.log(JSON.stringify(walletData, null, 2));
    
    return address.getId();
  } catch (error) {
    console.error('Error:', error.message);
    throw error;
  }
}

createOrGetWallet()
  .then(address => {
    console.log('\n✅ Use this address for PAYMENT_ADDRESS:', address);
    process.exit(0);
  })
  .catch(error => {
    console.error('Failed:', error);
    process.exit(1);
  });
