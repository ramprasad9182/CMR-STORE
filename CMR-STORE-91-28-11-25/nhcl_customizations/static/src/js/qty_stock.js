/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

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
          receipts:   { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          main_damage_JC:  { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          damage_main_JC:   { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          return_main_JC:   { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          delivery_orders:   { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          good_return_damage:   { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          pos_orders:  { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          manufacturing:  { done: 0, ready: 0, done_display: "0", ready_display: "0" },
          pos_exchange:  { done: 0, ready: 0, done_display: "0", ready_display: "0" },
        });
        onWillStart(async () => {
            await Promise.all([
                this.fetchReceiptsTotals(),
                this.fetchMainDamageJCTotals(),
                this.fetchDamageMainJCTotals(),
                this.fetchReturnJCTotals(),
                this.fetchDeliveryOrdersTotals(),
                this.fetchGoodsReturnDamageTotals(),
                this.fetchPosOrdersTotals(),
                this.fetchManufacturingTotals(),
                this.fetchPosExchangeTotals(),
            ]);
        });
    }



    async fetchReceiptsTotals() {
      try {
        // Call server method WITHOUT sending any domain (server uses literal domain)
        const res = await this.orm.call(
          "stock.picking.type",
          "get_receipts_totals",
          [],
          { kwargs: {} } // intentionally empty
        );

        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        if (!this.state.receipts) {
          this.state.receipts = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }

        // Update object properties (do not overwrite the object)
        this.state.receipts.done = done;
        this.state.receipts.ready = ready;
        this.state.receipts.done_display  = _fmt(done);
        this.state.receipts.ready_display = _fmt(ready);

        console.log("[fetchReceiptsTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchReceiptsTotals] failed:", err);

        if (!this.state.receipts) {
          this.state.receipts = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        } else {
          // ensure properties exist and are reset
          this.state.receipts.done = 0;
          this.state.receipts.ready = 0;
          this.state.receipts.done_display = "0";
          this.state.receipts.ready_display = "0";
        }
      }
    }

     async fetchMainDamageJCTotals(filters = {}) {
      try {
        const res = await this.orm.call(
          "stock.picking.type",
          "get_main_damage_totals",
          [],
          { kwargs: filters }
        );
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        if (!this.state.main_damage_JC) {
          this.state.main_damage_JC = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }

        this.state.main_damage_JC.done = done;
        this.state.main_damage_JC.ready = ready;
        this.state.main_damage_JC.done_display  = _fmt(done);
        this.state.main_damage_JC.ready_display = _fmt(ready);

        console.log("[fetchMainDamageJCTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchMainDamageJCTotals] failed:", err);

        if (!this.state.main_damage_JC) {
          this.state.main_damage_JC = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }
        this.state.main_damage_JC.done = 0;
        this.state.main_damage_JC.ready = 0;
        this.state.main_damage_JC.done_display = "0";
        this.state.main_damage_JC.ready_display = "0";

        if (this.notification && typeof this.notification.add === "function") {
          this.notification.add("Failed to load Main Damage (JC) totals.", { type: "danger" });
        }
        return { done: 0, ready: 0 };
      }
    }

     async fetchDamageMainJCTotals(filters = {}) {
      try {
        const res = await this.orm.call(
          "stock.picking.type",
          "get_damage_main_totals",
          [],
          { kwargs: filters }
        );
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        if (!this.state.damage_main_JC) {
          this.state.damage_main_JC = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }

        this.state.damage_main_JC.done = done;
        this.state.damage_main_JC.ready = ready;
        this.state.damage_main_JC.done_display  = _fmt(done);
        this.state.damage_main_JC.ready_display = _fmt(ready);

        console.log("[fetchdamage_main_JCTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchdamage_main_JCTotals] failed:", err);

        if (!this.state.damage_main_JC) {
          this.state.damage_main_JC = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }
        this.state.damage_main_JC.done = 0;
        this.state.damage_main_JC.ready = 0;
        this.state.damage_main_JC.done_display = "0";
        this.state.damage_main_JC.ready_display = "0";

        if (this.notification && typeof this.notification.add === "function") {
          this.notification.add("Failed to load damage_main_JC (JC) totals.", { type: "danger" });
        }
        return { done: 0, ready: 0 };
      }
    }

     async fetchReturnJCTotals(filters = {}) {
      try {
        const res = await this.orm.call(
          "stock.picking.type",
          "get_return_main_totals",
          [],
          { kwargs: filters }
        );
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        if (!this.state.return_main_JC) {
          this.state.return_main_JC = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }

        this.state.return_main_JC.done = done;
        this.state.return_main_JC.ready = ready;
        this.state.return_main_JC.done_display  = _fmt(done);
        this.state.return_main_JC.ready_display = _fmt(ready);

        console.log("[fetchreturn_main_JCTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchreturn_main_JCTotals] failed:", err);

        if (!this.state.return_main_JC) {
          this.state.return_main_JC = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }
        this.state.return_main_JC.done = 0;
        this.state.return_main_JC.ready = 0;
        this.state.return_main_JC.done_display = "0";
        this.state.return_main_JC.ready_display = "0";

        if (this.notification && typeof this.notification.add === "function") {
          this.notification.add("Failed to load return_main_JC (JC) totals.", { type: "danger" });
        }
        return { done: 0, ready: 0 };
      }
    }

     async fetchDeliveryOrdersTotals(filters = {}) {
      try {
        const res = await this.orm.call(
          "stock.picking.type",
          "get_delivery_orders_totals",
          [],
          { kwargs: filters }
        );
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        if (!this.state.delivery_orders) {
          this.state.delivery_orders = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }

        this.state.delivery_orders.done = done;
        this.state.delivery_orders.ready = ready;
        this.state.delivery_orders.done_display  = _fmt(done);
        this.state.delivery_orders.ready_display = _fmt(ready);

        console.log("[fetchdelivery_ordersTotals] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[fetchdelivery_ordersTotals] failed:", err);

        if (!this.state.delivery_orders) {
          this.state.delivery_orders = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }
        this.state.delivery_orders.done = 0;
        this.state.delivery_orders.ready = 0;
        this.state.delivery_orders.done_display = "0";
        this.state.delivery_orders.ready_display = "0";

        if (this.notification && typeof this.notification.add === "function") {
          this.notification.add("Failed to load delivery_orders (JC) totals.", { type: "danger" });
        }
        return { done: 0, ready: 0 };
      }
    }

     async fetchGoodsReturnDamageTotals(filters = {}) {
      try {
        const res = await this.orm.call(
          "stock.picking.type",
          "get_good_return_damage_totals",
          [],
          { kwargs: filters }
        );
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        if (!this.state.good_return_damage) {
          this.state.good_return_damage = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }

        this.state.good_return_damage.done = done;
        this.state.good_return_damage.ready = ready;
        this.state.good_return_damage.done_display  = _fmt(done);
        this.state.good_return_damage.ready_display = _fmt(ready);

        console.log("[good_return_damage] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[good_return_damage] failed:", err);

        if (!this.state.good_return_damage) {
          this.state.good_return_damage = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }
        this.state.good_return_damage.done = 0;
        this.state.good_return_damage.ready = 0;
        this.state.good_return_damage.done_display = "0";
        this.state.good_return_damage.ready_display = "0";

        if (this.notification && typeof this.notification.add === "function") {
          this.notification.add("Failed to load good_return_damage (JC) totals.", { type: "danger" });
        }
        return { done: 0, ready: 0 };
      }
    }

     async fetchPosOrdersTotals(filters = {}) {
      try {
        const res = await this.orm.call(
          "stock.picking.type",
          "get_PoS_Orders_totals",
          [],
          { kwargs: filters }
        );
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        if (!this.state.pos_orders) {
          this.state.pos_orders = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }

        this.state.pos_orders.done = done;
        this.state.pos_orders.ready = ready;
        this.state.pos_orders.done_display  = _fmt(done);
        this.state.pos_orders.ready_display = _fmt(ready);

        console.log("[pos_orders] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[pos_orders] failed:", err);

        if (!this.state.pos_orders) {
          this.state.pos_orders = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }
        this.state.pos_orders.done = 0;
        this.state.pos_orders.ready = 0;
        this.state.pos_orders.done_display = "0";
        this.state.pos_orders.ready_display = "0";

        if (this.notification && typeof this.notification.add === "function") {
          this.notification.add("Failed to load pos_orders (JC) totals.", { type: "danger" });
        }
        return { done: 0, ready: 0 };
      }
    }

     async fetchManufacturingTotals(filters = {}) {
      try {
        const res = await this.orm.call(
          "stock.picking.type",
          "get_manufacturing_totals",
          [],
          { kwargs: filters }
        );
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        if (!this.state.manufacturing) {
          this.state.manufacturing = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }

        this.state.manufacturing.done = done;
        this.state.manufacturing.ready = ready;
        this.state.manufacturing.done_display  = _fmt(done);
        this.state.manufacturing.ready_display = _fmt(ready);

        console.log("[manufacturing] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[manufacturing] failed:", err);

        if (!this.state.manufacturing) {
          this.state.manufacturing = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }
        this.state.manufacturing.done = 0;
        this.state.manufacturing.ready = 0;
        this.state.manufacturing.done_display = "0";
        this.state.manufacturing.ready_display = "0";

        if (this.notification && typeof this.notification.add === "function") {
          this.notification.add("Failed to load manufacturing (JC) totals.", { type: "danger" });
        }
        return { done: 0, ready: 0 };
      }
    }

     async fetchPosExchangeTotals(filters = {}) {
      try {
        const res = await this.orm.call(
          "stock.picking.type",
          "get_pos_exchange_totals",
          [],
          { kwargs: filters }
        );
        const done  = _parseNumber(res?.done ?? res?.total ?? res?.qty ?? res) || 0;
        const ready = _parseNumber(res?.ready ?? res?.assigned ?? res?.product_uom_qty ?? 0) || 0;

        if (!this.state.pos_exchange) {
          this.state.pos_exchange = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }

        this.state.pos_exchange.done = done;
        this.state.pos_exchange.ready = ready;
        this.state.pos_exchange.done_display  = _fmt(done);
        this.state.pos_exchange.ready_display = _fmt(ready);

        console.log("[pos_exchange] done:", done, "ready:", ready);
        return { done, ready };
      } catch (err) {
        console.error("[pos_exchange] failed:", err);

        if (!this.state.pos_exchange) {
          this.state.pos_exchange = { done: 0, ready: 0, done_display: "0", ready_display: "0" };
        }
        this.state.pos_exchange.done = 0;
        this.state.pos_exchange.ready = 0;
        this.state.pos_exchange.done_display = "0";
        this.state.pos_exchange.ready_display = "0";

        if (this.notification && typeof this.notification.add === "function") {
          this.notification.add("Failed to load pos_exchange (JC) totals.", { type: "danger" });
        }
        return { done: 0, ready: 0 };
      }
    }


}

registry.category("actions").add("StockOwlDashboard", StockOwlDashboard);








