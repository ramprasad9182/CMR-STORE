/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order, Orderline } from "@point_of_sale/app/store/models";

// ------- toggles -------
const AUTO_APPLY_PRODUCT_REWARDS = false; // true if you also want free-product rewards

// ------- capture originals SAFELY (may be undefined depending on load order) -------
const _origAddProduct       = typeof Order.prototype.add_product      === "function" ? Order.prototype.add_product      : null;
const _origRemoveOrderline  = typeof Order.prototype.remove_orderline === "function" ? Order.prototype.remove_orderline : null;
const _origSetPartner       = typeof Order.prototype.set_partner      === "function" ? Order.prototype.set_partner      : null;
const _origSetPricelist     = typeof Order.prototype.set_pricelist    === "function" ? Order.prototype.set_pricelist    : null;

const _origSetQuantity      = typeof Orderline.prototype.set_quantity   === "function" ? Orderline.prototype.set_quantity   : null;
const _origSetUnitPrice     = typeof Orderline.prototype.set_unit_price === "function" ? Orderline.prototype.set_unit_price : null;
const _origSetDiscount      = typeof Orderline.prototype.set_discount   === "function" ? Orderline.prototype.set_discount   : null;

// ------- helpers -------
const EPS = 0.01;

function _groupBy(arr, keyFn) {
    const m = {};
    for (const x of arr || []) {
        const k = keyFn(x);
        if (k == null) continue;
        (m[k] ||= []).push(x);
    }
    return m;
}

function _appliedProgramIds(order) {
    const ids = new Set();
    for (const line of order.get_orderlines() || []) {
        if (!line.is_reward_line) continue;
        const r = order.pos.reward_by_id?.[line.reward_id];
        const pid = r?.program_id?.id;
        if (pid) ids.add(pid);
    }
    return ids;
}

function _currentProgramDiscount(order, programId) {
    let total = 0;
    for (const line of order.get_orderlines() || []) {
        if (!line.is_reward_line) continue;
        const r = order.pos.reward_by_id?.[line.reward_id];
        if (r?.program_id?.id === programId) {
            total += Math.abs(line.get_display_price() * line.get_quantity());
        }
    }
    return total;
}

function _orderBaseAmount(order) {
    const lines = (order.get_orderlines() || []).filter(
        (l) => !l.is_reward_line && !l.display_is_total_discount
    );
    return lines.reduce((s, l) => s + l.get_price_with_tax() * l.get_quantity(), 0);
}

function _estimateIntended(reward, base) {
    if (reward.reward_type === "discount") return AUTO_APPLY_PRODUCT_REWARDS ? 1 : 0;
    return reward.discount_mode === "percentage"
        ? ((reward.discount ?? 0) / 100) * base
        : (reward.discount ?? 0);
}

function _getClaimables(order) {
    const claimable = order.getClaimableRewards ? order.getClaimableRewards() : [];
    // exclude eWallet programs
    return claimable.filter(({ reward }) => reward?.program_id?.program_type !== "ewallet");
}

// SAFE line removal: no recursion, no missing original
function _safeRemoveLine(order, line) {
    // Prefer low-level collection remove to avoid calling our own wrapper
    if (order?.orderlines?.remove) {
        order.orderlines.remove(line);
        return;
    }
    // Fallback to original remove if it exists
    if (_origRemoveOrderline) {
        _origRemoveOrderline.call(order, line);
        return;
    }
    // Last resort: set qty to 0
    if (typeof line?.set_quantity === "function") {
        line.set_quantity(0);
    }
}

// Remove all reward lines for a given program
function _removeProgramRewardLines(order, programId) {
    const lines = [...(order.get_orderlines() || [])];
    for (const line of lines) {
        if (!line.is_reward_line) continue;
        const reward = order.pos.reward_by_id?.[line.reward_id];
        if (reward.reward_type === 'discount' && reward?.program_id?.id === programId) {
            _safeRemoveLine(order, line);
        }
    }
}

// Choose best inside a program:
//  - Prefer capped discounts by largest cap
//  - Else highest discount %/amount
//  - Optionally product rewards

function _pickBestInsideProgram(items) {
    if (!items.length) return null;
    const discounts = items.filter((x) => x.reward?.reward_type === "discount");

    if (discounts.length) {
        const capped = discounts.filter((x) => (x.reward?.discount_max_amount ?? 0) > 0);
        if (capped.length) {
            return capped.slice().sort(
                (a, b) => (b.reward.discount_max_amount ?? 0) - (a.reward.discount_max_amount ?? 0)
            )[0];
        }
        return discounts.slice().sort(
            (a, b) => (b.reward?.discount ?? 0) - (a.reward?.discount ?? 0)
        )[0];
    }
    return null;
}

// ------- main patch: Order -------
patch(Order.prototype, {
    _scheduleAutoRewards() {
        if (this._autoRewardsBusy) return;
        clearTimeout(this._autoRewardsTimer);
        this._autoRewardsTimer = setTimeout(() => this._recomputeAutoRewards(), 0);
    },

    async _recomputeAutoRewards() {
        if (this._autoRewardsBusy) return;
        this._autoRewardsBusy = true;
        try {
            const base = _orderBaseAmount(this);

            // Consider programs currently applied OR currently claimable
            const appliedIds      = _appliedProgramIds(this);
            const firstClaimables = _getClaimables(this);
            const claimableIds    = new Set(firstClaimables.map((x) => x.reward?.program_id?.id).filter(Boolean));
            const programsToCheck = new Set([...appliedIds, ...claimableIds]);

            for (const pid of programsToCheck) {
                // Suppress current program’s reward lines so engine can surface bigger rules
                const currentAppliedAmt = _currentProgramDiscount(this, pid);
                _removeProgramRewardLines(this, pid);

                // Re-query claimables for THIS program only
                const nowClaimables = _getClaimables(this).filter((x) => x.reward?.program_id?.id === pid);
                if (!nowClaimables.length) {
                    // nothing valid → keep it off
                    continue;
                }

                const best = _pickBestInsideProgram(nowClaimables);
                if (!best) continue;

                // Decide if we should upgrade: different rule or greater allowed amount
                const intended = _estimateIntended(best.reward, base);
                const cap      = best.reward.discount_max_amount ?? 0;
                const allowed  = cap > 0 ? Math.min(intended, cap) : intended;

                const shouldUpgrade = allowed > currentAppliedAmt + EPS;
                // Even if not strictly "bigger", re-apply best to keep lines consistent
                if (shouldUpgrade || true) {
                    await this._applyReward(best.reward, best.coupon_id, best.potentialQty);
                }
            }
        } finally {
            this._autoRewardsBusy = false;
        }
    },

    // --- user-facing mutators (safe wrappers) ---
    add_product() {
        const res = _origAddProduct ? _origAddProduct.apply(this, arguments) : undefined;
        this._scheduleAutoRewards?.();
        return res;
    },

    remove_orderline(line) {
        _safeRemoveLine(this, line);
        this._scheduleAutoRewards?.();
        return;
    },

    set_partner() {
        const res = _origSetPartner ? _origSetPartner.apply(this, arguments) : undefined;
        this._scheduleAutoRewards?.();
        return res;
    },

    set_pricelist() {
        const res = _origSetPricelist ? _origSetPricelist.apply(this, arguments) : undefined;
        this._scheduleAutoRewards?.();
        return res;
    },
});

// ------- patch Orderline once (react to qty/price/discount changes) -------
patch(Orderline.prototype, {
    set_quantity() {
        const res = _origSetQuantity ? _origSetQuantity.apply(this, arguments) : undefined;
        this.order?._scheduleAutoRewards?.();
        return res;
    },
    set_unit_price() {
        const res = _origSetUnitPrice ? _origSetUnitPrice.apply(this, arguments) : undefined;
        this.order?._scheduleAutoRewards?.();
        return res;
    },
    set_discount() {
        const res = _origSetDiscount ? _origSetDiscount.apply(this, arguments) : undefined;
        this.order?._scheduleAutoRewards?.();
        return res;
    },
});
