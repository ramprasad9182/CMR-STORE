/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

// --- helpers (top-level functions) ---
function _parseNumber(v) {
  if (v == null) return 0;
  if (typeof v === "number") return v;
  const cleaned = String(v).replace(/[^\d.\-]/g, "");
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : 0;
}
function _fmt(n) {
  return (Math.abs(n - Math.round(n)) < 1e-9)
    ? new Intl.NumberFormat().format(Math.round(n))
    : new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

export class StockOwlDashboard extends Component {
    static template = "StockOwlDashboard";

    setup() {

        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
          receipts:                { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          internal_transfers:      { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          delivery_orders:         { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          pos_orders:              { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          manufacturing:           { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          resupply_subcontractor:  { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          dropship:                { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          dropship_subcontractor:  { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          vendor_return:           { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          damage_receipts:         { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          product_exchange_pos:    { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          receipts_damage:         { done: 0, ready: 0, done_display: "0", ready_display: "0" },
        });
        onWillStart(async () => {
            await Promise.all([
                this.fetchReceiptTotals(),
                this.fetchInternalTransfersTotals(),
                this.fetchDeliveryOrdersTotals(),
                this.fetchPosOrdersTotals(),
                this.fetchManufacturingTotals(),
                this.fetchResupplySubcontractorTotals(),
                this.fetchDropshipSubcontractorTotals(),
                this.fetchVendorReturnTotals(),
                this.fetchDamageReceiptsTotals(),
                this.fetchProductExchangePosTotals(),
                this.fetchReceiptsDamageTotals(),
                this.fetchDropshipTotals(),
            ]);
        });
    }
    // call this from inside your OWL component (this.orm must be available via useService)
    async fetchReceiptTotals(filters = {}) {
      const parseNumber = v => {
        if (v == null) return 0;
        if (typeof v === "number") return v;
        const cleaned = String(v).replace(/[^\d.\-]/g, "");
        const n = Number(cleaned);
        return Number.isFinite(n) ? n : 0;
      };
      const fmt = n => (Math.abs(n - Math.round(n)) < 1e-9)
        ? new Intl.NumberFormat().format(Math.round(n))
        : new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);

      try {
        const res = await this.orm.call(
          "stock.picking.type",
          "get_receipts_totals",
          [],
          { kwargs: filters }
        );

        // normalize
        const done = parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        // ensure state shape
        if (!this.state.receipts) this.state.receipts = { done: 0, ready: 0, done_display: "0", ready_display: "0" };

        // numeric values (for logic)
        this.state.receipts.done = done;
        this.state.receipts.ready = ready;

        // formatted strings (for UI)
        this.state.receipts.done_display = fmt(done);
        this.state.receipts.ready_display = fmt(ready);

        console.log("[fetchReceiptTotals] done:", done, "ready:", ready, "done_display:", this.state.receipts.done_display);

        return { done, ready };
      } catch (err) {
        console.error("[fetchReceiptTotals] failed:", err);
        if (!this.state.receipts) this.state.receipts = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.receipts.done = 0;
        this.state.receipts.ready = 0;
        this.state.receipts.done_display = "0";
        this.state.receipts.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") {
          this.notification.add("Failed to load Receipts totals.", { type: "danger" });
        }
        return { done: 0, ready: 0 };
      }
    }

    async fetchInternalTransfersTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_internal_transfers_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.internal_transfers) this.state.internal_transfers = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.internal_transfers.done = done;
        this.state.internal_transfers.ready = ready;
        this.state.internal_transfers.done_display = _fmt(done);
        this.state.internal_transfers.ready_display = _fmt(ready);
        console.log("[fetchInternalTransfersTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchInternalTransfersTotals] failed", err);
        if (!this.state.internal_transfers) this.state.internal_transfers = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.internal_transfers.done = 0;
        this.state.internal_transfers.ready = 0;
        this.state.internal_transfers.done_display = "0";
        this.state.internal_transfers.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Internal Transfers totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchDeliveryOrdersTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_delivery_orders_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.delivery_orders) this.state.delivery_orders = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.delivery_orders.done = done;
        this.state.delivery_orders.ready = ready;
        this.state.delivery_orders.done_display = _fmt(done);
        this.state.delivery_orders.ready_display = _fmt(ready);
        console.log("[fetchDeliveryOrdersTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchDeliveryOrdersTotals] failed", err);
        if (!this.state.delivery_orders) this.state.delivery_orders = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.delivery_orders.done = 0;
        this.state.delivery_orders.ready = 0;
        this.state.delivery_orders.done_display = "0";
        this.state.delivery_orders.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Delivery Orders totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchPosOrdersTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_pos_orders_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.pos_orders) this.state.pos_orders = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.pos_orders.done = done;
        this.state.pos_orders.ready = ready;
        this.state.pos_orders.done_display = _fmt(done);
        this.state.pos_orders.ready_display = _fmt(ready);
        console.log("[fetchPosOrdersTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchPosOrdersTotals] failed", err);
        if (!this.state.pos_orders) this.state.pos_orders = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.pos_orders.done = 0;
        this.state.pos_orders.ready = 0;
        this.state.pos_orders.done_display = "0";
        this.state.pos_orders.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load PoS totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchManufacturingTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_manufacturing_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.manufacturing) this.state.manufacturing = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.manufacturing.done = done;
        this.state.manufacturing.ready = ready;
        this.state.manufacturing.done_display = _fmt(done);
        this.state.manufacturing.ready_display = _fmt(ready);
        console.log("[fetchManufacturingTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchManufacturingTotals] failed", err);
        if (!this.state.manufacturing) this.state.manufacturing = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.manufacturing.done = 0;
        this.state.manufacturing.ready = 0;
        this.state.manufacturing.done_display = "0";
        this.state.manufacturing.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Manufacturing totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchResupplySubcontractorTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_resupply_subcontractor_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.resupply_subcontractor) this.state.resupply_subcontractor = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.resupply_subcontractor.done = done;
        this.state.resupply_subcontractor.ready = ready;
        this.state.resupply_subcontractor.done_display = _fmt(done);
        this.state.resupply_subcontractor.ready_display = _fmt(ready);
        console.log("[fetchResupplySubcontractorTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchResupplySubcontractorTotals] failed", err);
        if (!this.state.resupply_subcontractor) this.state.resupply_subcontractor = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.resupply_subcontractor.done = 0;
        this.state.resupply_subcontractor.ready = 0;
        this.state.resupply_subcontractor.done_display = "0";
        this.state.resupply_subcontractor.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Resupply Subcontractor totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchDropshipTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_dropship_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.dropship) this.state.dropship = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.dropship.done = done;
        this.state.dropship.ready = ready;
        this.state.dropship.done_display = _fmt(done);
        this.state.dropship.ready_display = _fmt(ready);
        console.log("[fetchDropshipTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchDropshipTotals] failed", err);
        if (!this.state.dropship) this.state.dropship = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.dropship.done = 0;
        this.state.dropship.ready = 0;
        this.state.dropship.done_display = "0";
        this.state.dropship.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Dropship totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchDropshipSubcontractorTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_dropship_subcontractor_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.dropship_subcontractor) this.state.dropship_subcontractor = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.dropship_subcontractor.done = done;
        this.state.dropship_subcontractor.ready = ready;
        this.state.dropship_subcontractor.done_display = _fmt(done);
        this.state.dropship_subcontractor.ready_display = _fmt(ready);
        console.log("[fetchDropshipSubcontractorTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchDropshipSubcontractorTotals] failed", err);
        if (!this.state.dropship_subcontractor) this.state.dropship_subcontractor = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.dropship_subcontractor.done = 0;
        this.state.dropship_subcontractor.ready = 0;
        this.state.dropship_subcontractor.done_display = "0";
        this.state.dropship_subcontractor.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Dropship Subcontractor totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchVendorReturnTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_vendor_return_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.vendor_return) this.state.vendor_return = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.vendor_return.done = done;
        this.state.vendor_return.ready = ready;
        this.state.vendor_return.done_display = _fmt(done);
        this.state.vendor_return.ready_display = _fmt(ready);
        console.log("[fetchVendorReturnTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchVendorReturnTotals] failed", err);
        if (!this.state.vendor_return) this.state.vendor_return = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.vendor_return.done = 0;
        this.state.vendor_return.ready = 0;
        this.state.vendor_return.done_display = "0";
        this.state.vendor_return.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Vendor Return totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchDamageReceiptsTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_damage_receipts_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.damage_receipts) this.state.damage_receipts = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.damage_receipts.done = done;
        this.state.damage_receipts.ready = ready;
        this.state.damage_receipts.done_display = _fmt(done);
        this.state.damage_receipts.ready_display = _fmt(ready);
        console.log("[fetchDamageReceiptsTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchDamageReceiptsTotals] failed", err);
        if (!this.state.damage_receipts) this.state.damage_receipts = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.damage_receipts.done = 0;
        this.state.damage_receipts.ready = 0;
        this.state.damage_receipts.done_display = "0";
        this.state.damage_receipts.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Damage Receipts totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchProductExchangePosTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_product_exchange_pos_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.product_exchange_pos) this.state.product_exchange_pos = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.product_exchange_pos.done = done;
        this.state.product_exchange_pos.ready = ready;
        this.state.product_exchange_pos.done_display = _fmt(done);
        this.state.product_exchange_pos.ready_display = _fmt(ready);
        console.log("[fetchProductExchangePosTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchProductExchangePosTotals] failed", err);
        if (!this.state.product_exchange_pos) this.state.product_exchange_pos = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.product_exchange_pos.done = 0;
        this.state.product_exchange_pos.ready = 0;
        this.state.product_exchange_pos.done_display = "0";
        this.state.product_exchange_pos.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Product Exchange totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }

    async fetchReceiptsDamageTotals(filters = {}) {
      try {
        const res = await this.orm.call("stock.picking.type", "get_receipts_damage_totals", [], { kwargs: filters });
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;
        if (!this.state.receipts_damage) this.state.receipts_damage = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.receipts_damage.done = done;
        this.state.receipts_damage.ready = ready;
        this.state.receipts_damage.done_display = _fmt(done);
        this.state.receipts_damage.ready_display = _fmt(ready);
        console.log("[fetchReceiptsDamageTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchReceiptsDamageTotals] failed", err);
        if (!this.state.receipts_damage) this.state.receipts_damage = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        this.state.receipts_damage.done = 0;
        this.state.receipts_damage.ready = 0;
        this.state.receipts_damage.done_display = "0";
        this.state.receipts_damage.ready_display = "0";
        if (this.notification && typeof this.notification.add === "function") this.notification.add("Failed to load Receipts Damage totals.", { type: "danger" });
        return { done: 0, ready: 0 };
      }
    }



}

registry.category("actions").add("StockOwlDashboard", StockOwlDashboard);








