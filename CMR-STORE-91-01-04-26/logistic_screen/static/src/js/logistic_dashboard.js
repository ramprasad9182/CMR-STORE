/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, useState } = owl;
const actionRegistry = registry.category("actions");

export class LogisticDashboard extends Component {

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            // Status bars 1.2
            status: { total: 0, delivered: 0, in_transit: 0, delayed: 0, canceled: 0 },
            loadingStatus: true,
            // state additions
            draft: {today: 0, week: 0, month: 0},  // upcoming (state=draft) 3.1
            done: { today: 0, week: 0, month: 0},  // delivered (state=done)1.1
            loadingDelivery: true,
            // partialDelivered 2.1
            partialDelivered: 0,
            loadingPartialDelivered: true,
            // top unopened divisions 2.2
             unopenedDivision: { total: 0, items: [] },
             loadingUnopenedDivision: true,
             // topProducts 3.2
            topProducts: { total: 0, max: 0, items: [] },
            loadingTopProducts: true,
            // top divisions - bales 3.3
             unopenedDivisionBales: { total: 0, items: [] },
             loadingUnopenedDivisionBales: true,
            // openParcel 2.3
            openParcel: { draft: 0, done: 0, total: 0 },
            loadingOpenParcel: true,
            // 1) state additions (in your useState initial object)
            openParcel: { draft: 0, done: 0},
            loadingOpenParcel: true,

        });

        // % of total (for horizontal bars)
        this.pct = (n, total) => {
          const t = Number(total || 0), v = Number(n || 0);
          if (!t) return 0;
          return Math.max(0, Math.min(100, Math.round((v * 100) / t)));
        };

        // height % vs max (for columns)
        this.hPct = (v) => {
          const m = Number(this.state.topProducts.max || 0);
          const n = Number(v || 0);
          if (!m) return 0;
          return Math.round((n * 100) / m);
         };
        onWillStart(async () => {
            this.fetchDeliveryPeriods(),
            this.fetchLRStatus(),
            this.fetchPartialDelivered(),
            this.fetchDivisionBales(),
            this.fetchOpenParcelCounts()


        });
    }

    async fetchDeliveryPeriods(filters = {}) {
      try {
        const res = await this.orm.call(
          "logistic.screen.data",
          "get_delivery_period_counts",
          [],
          { kwargs: filters }
        );

        const d = (res && res.draft) || {};
        const dn = (res && res.done)  || {};

        this.state.draft = {
          today: Number(d.today || 0),
          week:  Number(d.week  || 0),
          month: Number(d.month || 0),
        };
        this.state.done = {
          today: Number(dn.today || 0),
          week:  Number(dn.week  || 0),
          month: Number(dn.month || 0),
        };
      } catch (e) {
        console.error("Delivery period counts fetch failed:", e);
        this.notification.add("Failed to load Upcoming/Delivered counts.", { type: "danger" });
      } finally {
        this.state.loadingDelivery = false;
      }
    }

    async fetchLRStatus() {
      try {
        const [a, b] = await Promise.all([
          this.orm.call("logistic.screen.data", "get_status_delivered", [], {}),
          this.orm.call("logistic.screen.data", "get_status_transit_delayed", [], {}),
        ]);

        const delivered  = Number((a && a.delivered) || 0);
        const in_transit = Number((b && b.in_transit) || 0);
        const delayed    = Number((b && b.delayed) || 0);
        const canceled   = Number((b && b.canceled) || 0); // 0 for now

        const total = delivered + in_transit + delayed + canceled;
        this.state.status = { total, delivered, in_transit, delayed, canceled };
      } catch (e) {
        console.error("Status fetch failed:", e);
        this.notification.add("Failed to load LR status.", { type: "danger" });
      } finally {
        this.state.loadingStatus = false;
      }
    }

    async fetchPartialDelivered(filters = {}) {
      try {
        const res = await this.orm.call(
          "logistic.screen.data",
          "get_partial_delivered_count",
          [],
          { kwargs: filters }
        );
        const v = (res && res.partial_delivered) || 0;
        this.state.partialDelivered = Number(v);
      } catch (e) {
        console.error("Partial delivered fetch failed:", e);
        this.notification.add("Failed to load Partial Delivered LRs.", { type: "danger" });
      } finally {
        this.state.loadingPartialDelivered = false;
      }
    }

    async fetchDivisionBales(filters = {}) {
      try {
        this.state.loadingUnopenedDivisionBales = true;
        const res = await this.orm.call(
          "logistic.screen.data",
          "get_divisionwise_bale_totals",
          [5],
          { kwargs: filters }
        );
        const items = Array.isArray(res.results) ? res.results : [];
        this.state.unopenedDivisionBales = {
          total: items.length,
          items,
          delivery_ids: Array.isArray(res.delivery_ids) ? res.delivery_ids : [],
          division_delivery_ids: (res.division_delivery_ids && typeof res.division_delivery_ids === 'object') ? res.division_delivery_ids : {},
        };
      } catch (e) {
        console.error("Unopened division bales fetch failed:", e);
        this.notification.add("Failed to load unopened division bales counts.", { type: "danger" });
        this.state.unopenedDivisionBales = { total: 0, items: [], delivery_ids: [], division_delivery_ids: {} };
      } finally {
        this.state.loadingUnopenedDivisionBales = false;
      }
    }

    async fetchOpenParcelCounts(filters = {}) {
      try {
        const res = await this.orm.call(
          "logistic.screen.data",
          "get_open_parcel_state_counts",
          [],
          { kwargs: filters }
        );
        const draft = Number((res && res.draft) || 0);
        const done  = Number((res && res.done)  || 0);
        this.state.openParcel = { draft, done };
      } catch (e) {
        console.error("Open parcel counts fetch failed:", e);
        this.notification.add("Failed to load Open Parcel counts.", { type: "danger" });
      } finally {
        this.state.loadingOpenParcel = false;
      }
    }

    async fetchDeliveryPeriods(filters = {}) {
      try {
        const res = await this.orm.call(
          "logistic.screen.data",
          "get_delivery_period_counts",
          [],
          { kwargs: filters }
        );

        const d = (res && res.draft) || {};
        const dn = (res && res.done)  || {};

        this.state.draft = {
          today: Number(d.today || 0),
          week:  Number(d.week  || 0),
          month: Number(d.month || 0),
        };
        this.state.done = {
          today: Number(dn.today || 0),
          week:  Number(dn.week  || 0),
          month: Number(dn.month || 0),
        };
      } catch (e) {
        console.error("Delivery period counts fetch failed:", e);
        this.notification.add("Failed to load Upcoming/Delivered counts.", { type: "danger" });
      } finally {
        this.state.loadingDelivery = false;
      }
    }

    async fetchTop5Products(filters = {}) {
      try {
        const res = await this.orm.call(
          "logistic.screen.data",
          "get_top5_products_delivered",
          [],
          { kwargs: filters }
        );
        const total = (res && res.total) || 0;
        const max   = (res && res.max)   || 0;
        const items = (res && Array.isArray(res.items)) ? res.items : [];
        this.state.topProducts = { total: Number(total), max: Number(max), items };
      } catch (e) {
        console.error("Top 5 products fetch failed:", e);
        this.notification.add("Failed to load Top 5 Delivered Products.", { type: "danger" });
      } finally {
        this.state.loadingTopProducts = false;
      }
    }

    fmtINR(n) {
        return Number(n || 0).toLocaleString('en-IN',{
                style: 'currency', currency: 'INR', maximumFractionDigits: 0
        });
    }

    fmt(n) {
        return Number(n || 0).toLocaleString();
    }

    barPx(count, chartH = 140) {
      const max = Number(this.state.topProducts.max || 0);
      const c = Number(count || 0);
      if (!max) return 4;                        // tiny stub if no data
      return Math.max(4, Math.round((c * chartH) / max));
    }

    // helper to dispatch the action (modern service with fallback)
    _doAction = (action) => {
      const actionSvc = this.env?.services?.action || this.action;
      if (actionSvc && actionSvc.doAction) {
        return actionSvc.doAction(action);
      } else if (this.trigger) {
        return this.trigger("do-action", action);
      } else {
        console.warn("No action service available", action);
        return Promise.resolve();
      }
    };

    // Draft (upcoming)
    openDraftToday = () => {
      const today = new Date();
      const y = today.getFullYear(), m = String(today.getMonth() + 1).padStart(2,'0'), d = String(today.getDate()).padStart(2,'0');
      const start = `${y}-${m}-${d} 00:00:00`, end = `${y}-${m}-${d} 23:59:59`;
      const domain = [
        ['delivery_entry_types', '=', 'manual'],
        ['state', '=', 'draft'],
        ['logistic_date', '>=', start],
        ['logistic_date', '<=', end],
      ];
      this._doAction({
        type: 'ir.actions.act_window',
        name: 'Upcoming — Today',
        res_model: 'delivery.check',
        view_mode: 'tree,form',
        views: [[false,'tree'],[false,'form']],
        domain,
        target: 'current',
      });
    };

    openDraftWeek = () => {
      const today = new Date();
      const weekStart = new Date(); weekStart.setDate(today.getDate() - 6);
      const a = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')} 23:59:59`;
      const b = `${weekStart.getFullYear()}-${String(weekStart.getMonth()+1).padStart(2,'0')}-${String(weekStart.getDate()).padStart(2,'0')} 00:00:00`;
      const domain = [
        ['delivery_entry_types', '=', 'manual'],
        ['state', '=', 'draft'],
        ['logistic_date', '>=', b],
        ['logistic_date', '<=', a],
      ];
      this._doAction({
        type: 'ir.actions.act_window',
        name: 'Upcoming — Week',
        res_model: 'delivery.check',
        view_mode: 'tree,form',
        views: [[false,'tree'],[false,'form']],
        domain,
        target: 'current',
      });
    };

    openDraftMonth = () => {
      const today = new Date();
      const monthStart = new Date(); monthStart.setDate(today.getDate() - 29);
      const a = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')} 23:59:59`;
      const b = `${monthStart.getFullYear()}-${String(monthStart.getMonth()+1).padStart(2,'0')}-${String(monthStart.getDate()).padStart(2,'0')} 00:00:00`;
      const domain = [
        ['delivery_entry_types', '=', 'manual'],
        ['state', '=', 'draft'],
        ['logistic_date', '>=', b],
        ['logistic_date', '<=', a],
      ];
      this._doAction({
        type: 'ir.actions.act_window',
        name: 'Upcoming — Month',
        res_model: 'delivery.check',
        view_mode: 'tree,form',
        views: [[false,'tree'],[false,'form']],
        domain,
        target: 'current',
      });
    };

    // Done (delivered)
    openDoneToday = () => {
      const today = new Date();
      const y = today.getFullYear(), m = String(today.getMonth()+1).padStart(2,'0'), d = String(today.getDate()).padStart(2,'0');
      const start = `${y}-${m}-${d} 00:00:00`, end = `${y}-${m}-${d} 23:59:59`;
      const domain = [
        ['delivery_entry_types', '=', 'manual'],
        ['state', 'in', ['delivered','delivery','done']],
        ['logistic_date', '>=', start],
        ['logistic_date', '<=', end],
      ];
      this._doAction({
        type: 'ir.actions.act_window',
        name: 'Delivered — Today',
        res_model: 'delivery.check',
        view_mode: 'tree,form',
        views: [[false,'tree'],[false,'form']],
        domain,
        target: 'current',
      });
    };

    openDoneWeek = () => {
      const today = new Date();
      const weekStart = new Date(); weekStart.setDate(today.getDate() - 6);
      const a = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')} 23:59:59`;
      const b = `${weekStart.getFullYear()}-${String(weekStart.getMonth()+1).padStart(2,'0')}-${String(weekStart.getDate()).padStart(2,'0')} 00:00:00`;
      const domain = [
        ['delivery_entry_types', '=', 'manual'],
        ['state', 'in', ['delivered','delivery','done']],
        ['logistic_date', '>=', b],
        ['logistic_date', '<=', a],
      ];
      this._doAction({
        type: 'ir.actions.act_window',
        name: 'Delivered — Week',
        res_model: 'delivery.check',
        view_mode: 'tree,form',
        views: [[false,'tree'],[false,'form']],
        domain,
        target: 'current',
      });
    };

    openDoneMonth = () => {
      const today = new Date();
      const monthStart = new Date(); monthStart.setDate(today.getDate() - 29);
      const a = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')} 23:59:59`;
      const b = `${monthStart.getFullYear()}-${String(monthStart.getMonth()+1).padStart(2,'0')}-${String(monthStart.getDate()).padStart(2,'0')} 00:00:00`;
      const domain = [
        ['delivery_entry_types', '=', 'manual'],
        ['state', 'in', ['delivered','delivery','done']],
        ['logistic_date', '>=', b],
        ['logistic_date', '<=', a],
      ];
      this._doAction({
        type: 'ir.actions.act_window',
        name: 'Delivered — Month',
        res_model: 'delivery.check',
        view_mode: 'tree,form',
        views: [[false,'tree'],[false,'form']],
        domain,
        target: 'current',
      });
    };

    // Delivered: matches get_status_delivered (automatic + state = 'delivery')
    openStatusDelivered = () => {
      const action = {
        type: "ir.actions.act_window",
        name: "Delivered checks",
        res_model: "delivery.check",
        view_mode: "tree,form",
        views: [[false, "tree"], [false, "form"]],
        domain: [
          ['delivery_entry_types', '=', 'manual'],
          ['state', '=', 'delivery'],
        ],
        target: "current",
      };
      this._doAction(action);
    };

    // In Transit: matches get_status_transit_delayed in_transit (automatic + state = 'draft')
    openStatusInTransit = () => {
      const action = {
        type: "ir.actions.act_window",
        name: "In Transit checks",
        res_model: "delivery.check",
        view_mode: "tree,form",
        views: [[false, "tree"], [false, "form"]],
        domain: [
          ['delivery_entry_types', '=', 'manual'],
          ['state', '=', 'draft'],
        ],
        target: "current",
      };
      this._doAction(action);
    };

    // Delayed: matches get_status_transit_delayed delayed
    // Uses today's date (YYYY-MM-DD) computed client-side to match ('logistic_date', '>', today)
    openStatusDelayed = () => {
      // compute today's date in YYYY-MM-DD
      const today = new Date();
      const yyyy = today.getFullYear();
      const mm = String(today.getMonth() + 1).padStart(2, '0');
      const dd = String(today.getDate()).padStart(2, '0');
      const todayStr = `${yyyy}-${mm}-${dd}`;

      const action = {
        type: "ir.actions.act_window",
        name: "Delayed checks",
        res_model: "delivery.check",
        view_mode: "tree,form",
        views: [[false, "tree"], [false, "form"]],
        domain: [
          ['delivery_entry_types', '=', 'manual'],
          ['state', '=', 'done'],
          ['logistic_date', '>', todayStr],
        ],
        target: "current",
      };
      this._doAction(action);
    };

    // Canceled: matches get_status_transit_delayed canceled
    openStatusCanceled = () => {
      const action = {
        type: "ir.actions.act_window",
        name: "Canceled checks",
        res_model: "delivery.check",
        view_mode: "tree,form",
        views: [[false, "tree"], [false, "form"]],
        domain: [
          ['delivery_entry_types', '=', 'manual'],
          ['state', '=', 'cancel'],
        ],
        target: "current",
      };
      this._doAction(action);
    };

    openTopProduct = (categoryKey) => {
      if (!categoryKey) {
        this.notification?.add?.("No product category selected.", { type: "warning" });
        return;
      }

      // Simple, robust domain: match the parsed category text inside item_details (case-insensitive)
      const domain = [['item_details', 'ilike', categoryKey]];

      // Optionally: if you want to restrict to delivered entries only, add:
      // domain.push(['state', 'in', ['delivered','delivery','done']]);

      const action = {
        type: 'ir.actions.act_window',
        name: `Products: ${categoryKey}`,
        res_model: 'delivery.check',
        view_mode: 'tree,form',
        views: [[false, 'tree'], [false, 'form']],
        domain,
        target: 'current',
      };

      // call your existing helper
      this._doAction(action);
    };

    openPartialDelivered = () => {
      const action = {
        type: "ir.actions.act_window",
        name: "Partial Delivered",
        res_model: "delivery.check",
        view_mode: "tree,form",
        views: [[false, "tree"], [false, "form"]],
        domain: [
          ['delivery_entry_types', '=', 'manual'],
          ['overall_remaining_bales', '>=', 1],
          ['state', '=', 'delivery']
        ],
        target: "current",
      };

      const actionSvc = this.env?.services?.action || this.action;
      if (actionSvc && actionSvc.doAction) {
        actionSvc.doAction(action);
      } else if (this.trigger) {
        this.trigger("do-action", action);
      } else {
        console.warn("No action service available to open Partial Delivered action", action);
      }
    };

    // Open parcels with state = 'draft'
    openUnopenParcels = () => {
      const action = {
        type: 'ir.actions.act_window',
        name: 'Unopened Parcels (draft)',
        res_model: 'open.parcel',
        view_mode: 'tree,form',
        views: [[false, 'tree'], [false, 'form']],
        domain: [['state', '=', 'draft']],
        target: 'current',
      };
      if (this._doAction) {
        this._doAction(action);
      } else {
        const svc = this.env?.services?.action || this.action;
        if (svc && svc.doAction) svc.doAction(action);
        else if (this.trigger) this.trigger('do-action', action);
        else this.notification?.add?.("Cannot open parcels (no action service).", { type: "danger" });
      }
    };

    openDivisionDeliveries = (divisionName) => {
      if (!divisionName) {
        this.notification?.add?.("No division selected.", { type: "warning" });
        return;
      }

      // Try exact ids returned by server first (recommended)
      const map = (this.state.unopenedDivision && this.state.unopenedDivision.division_delivery_ids) || {};
      const ids = map[divisionName] || map[String(divisionName)] || [];

      let action;
      if (Array.isArray(ids) && ids.length) {
        action = {
          type: 'ir.actions.act_window',
          name: `Deliveries — ${divisionName}`,
          res_model: 'delivery.check',
          view_mode: 'tree,form',
          views: [[false, 'tree'], [false, 'form']],
          domain: [['id', 'in', ids]],
          target: 'current',
        };
      } else {
        // Fallback: simple ilike search on item_details so the click still shows relevant records
        action = {
          type: 'ir.actions.act_window',
          name: `Deliveries — ${divisionName}`,
          res_model: 'delivery.check',
          view_mode: 'tree,form',
          views: [[false, 'tree'], [false, 'form']],
          domain: [['item_details', 'ilike', divisionName]],
          target: 'current',
        };
      }

      this._doAction(action);
    };

    // Open parcels with state = 'done'
    openOpenParcels = () => {
      const action = {
        type: 'ir.actions.act_window',
        name: 'Open Parcels (done)',
        res_model: 'open.parcel',
        view_mode: 'tree,form',
        views: [[false, 'tree'], [false, 'form']],
        domain: [['state', '=', 'done']],
        target: 'current',
      };
      if (this._doAction) {
        this._doAction(action);
      } else {
        const svc = this.env?.services?.action || this.action;
        if (svc && svc.doAction) svc.doAction(action);
        else if (this.trigger) this.trigger('do-action', action);
        else this.notification?.add?.("Cannot open parcels (no action service).", { type: "danger" });
      }
    };

}

LogisticDashboard.template = "logistic_screen.logisticDashboard";
registry.category("actions").add("logistic_screen_tag", LogisticDashboard);