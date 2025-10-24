/**
 * Payment Tracker Service
 * Prevents payment replay attacks by tracking used payment IDs
 *
 * Security: Ensures each payment can only be used once
 */

class PaymentTracker {
  constructor(ttl = 3600000) { // Default: 1 hour TTL
    this.usedPayments = new Map();
    this.ttl = ttl; // Time to live in milliseconds

    // Cleanup old entries every 10 minutes
    this.cleanupInterval = setInterval(() => {
      this.cleanup();
    }, 600000);

    console.log('[PaymentTracker] Initialized with TTL:', ttl, 'ms');
  }

  /**
   * Check if a payment ID has been used
   * @param {string} paymentId - Payment transaction ID
   * @returns {boolean} true if payment was already used
   */
  isUsed(paymentId) {
    if (!paymentId) {
      return false;
    }

    const normalized = this.normalizePaymentId(paymentId);
    const entry = this.usedPayments.get(normalized);

    if (!entry) {
      return false;
    }

    // Check if entry has expired
    if (Date.now() - entry.timestamp > this.ttl) {
      this.usedPayments.delete(normalized);
      return false;
    }

    return true;
  }

  /**
   * Mark a payment ID as used
   * @param {string} paymentId - Payment transaction ID
   * @param {object} metadata - Optional metadata to store
   * @returns {boolean} true if successfully marked, false if already used
   */
  markUsed(paymentId, metadata = {}) {
    if (!paymentId) {
      throw new Error('Payment ID is required');
    }

    const normalized = this.normalizePaymentId(paymentId);

    // Check if already used
    if (this.isUsed(normalized)) {
      console.log('[PaymentTracker] Replay attack detected:', normalized);
      return false;
    }

    // Store payment with timestamp
    this.usedPayments.set(normalized, {
      timestamp: Date.now(),
      originalId: paymentId,
      metadata: metadata
    });

    console.log('[PaymentTracker] Payment marked as used:', normalized);
    return true;
  }

  /**
   * Normalize payment ID (remove tx_ prefix, lowercase)
   * @param {string} paymentId
   * @returns {string} normalized payment ID
   */
  normalizePaymentId(paymentId) {
    if (!paymentId || typeof paymentId !== 'string') {
      return '';
    }

    let normalized = paymentId.trim().toLowerCase();

    // Remove tx_ prefix if present
    if (normalized.startsWith('tx_')) {
      normalized = normalized.substring(3);
    }

    return normalized;
  }

  /**
   * Remove expired entries
   */
  cleanup() {
    const now = Date.now();
    let removed = 0;

    for (const [paymentId, entry] of this.usedPayments.entries()) {
      if (now - entry.timestamp > this.ttl) {
        this.usedPayments.delete(paymentId);
        removed++;
      }
    }

    if (removed > 0) {
      console.log(`[PaymentTracker] Cleaned up ${removed} expired payment(s). Active: ${this.usedPayments.size}`);
    }
  }

  /**
   * Get statistics about tracked payments
   * @returns {object} Statistics
   */
  getStats() {
    return {
      totalTracked: this.usedPayments.size,
      ttl: this.ttl,
      oldestEntry: this.getOldestEntryAge(),
      newestEntry: this.getNewestEntryAge()
    };
  }

  /**
   * Get age of oldest entry in milliseconds
   * @returns {number}
   */
  getOldestEntryAge() {
    if (this.usedPayments.size === 0) {
      return 0;
    }

    const now = Date.now();
    let oldest = 0;

    for (const entry of this.usedPayments.values()) {
      const age = now - entry.timestamp;
      if (age > oldest) {
        oldest = age;
      }
    }

    return oldest;
  }

  /**
   * Get age of newest entry in milliseconds
   * @returns {number}
   */
  getNewestEntryAge() {
    if (this.usedPayments.size === 0) {
      return 0;
    }

    const now = Date.now();
    let newest = Infinity;

    for (const entry of this.usedPayments.values()) {
      const age = now - entry.timestamp;
      if (age < newest) {
        newest = age;
      }
    }

    return newest;
  }

  /**
   * Clear all tracked payments (for testing)
   */
  clear() {
    this.usedPayments.clear();
    console.log('[PaymentTracker] All tracked payments cleared');
  }

  /**
   * Shutdown the payment tracker
   */
  shutdown() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    console.log('[PaymentTracker] Shutdown complete');
  }
}

// Singleton instance
let trackerInstance = null;

/**
 * Get or create the payment tracker instance
 * @param {number} ttl - Time to live in milliseconds
 * @returns {PaymentTracker}
 */
function getPaymentTracker(ttl) {
  if (!trackerInstance) {
    const ttlMs = ttl || parseInt(process.env.PAYMENT_CACHE_TTL_SECONDS || '3600') * 1000;
    trackerInstance = new PaymentTracker(ttlMs);
  }
  return trackerInstance;
}

module.exports = {
  PaymentTracker,
  getPaymentTracker
};
