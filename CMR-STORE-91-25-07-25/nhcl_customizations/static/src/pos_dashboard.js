/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc_service";
import { Component, useState, onWillStart  } from "@odoo/owl";

export class OwlPosDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.menuItems = [
          { id: 1, label: "CMR-Srikakulam", parent: "Store Name" },
        ];
        this.state = useState({
            models: [],
            selected: 1,
            lastParent: '',
            records: [],
            recordCount: 0,
            categoryList: [],
            selectedCategories: [],
            promo: [],
            selectedPromo: [],
            totalSrikakulam: 0,
            categorySummary: [],
            period:90,
        });
        this._loadData();
        this.loadCategorySummary();
        onWillStart(async () => {
             try {
                const domain = [['model', 'in', ['loyalty.program','product.category','pos.order.line','pos.order']]];
                const models = await this.orm.searchRead("ir.model", domain, ["name", "id"]);
                this.state.models = models || [];
            } catch (error) {
                console.error("Failed to fetch models:", error);
                this.state.models = []; // Fallback to an empty array if there's an error
            }
        });
        this.getTypeFromSelected = () => {
            const typeMap = {
                1: "CMR-Srikakulam",
            };
            return typeMap[this.state.selected];
        };
        this.selectMenu = this.selectMenu.bind(this);
        this.onPromoChange = this.onPromoChange.bind(this);
    }// Ends of setup

    selectMenu(id) {
        this.state.selected = id;
    }

    async onPromoChange(ev) {
        let tid = ev.target.value;
        if (tid !== "All") {
        tid = parseInt(tid, 1);           // convert "5" → 5
        }
        this.state.selectedPromo = tid;     // now matches t.id’s type
        //      await this.loadRecordsForSelectedType();
    }
    async loadCategorySummary() {
        const data = await this.orm.call("loyalty.program", "get_category_summary_from_active_promotions", []);
        this.state.categorySummary = data; // will trigger UI re-render
        this.state.recordCount = this.state.categorySummary.length;
    }


    async _loadData() {
        try {
        const [ParentProduct, ParentList, TotalPromo, PromoList] = await Promise.all([
                this.orm.call("product.category", "get_parent_product", {}),
                this.orm.call("product.category", "get_parent_product", {}),
                this.orm.call("loyalty.program", "get_total_promo", {}),
                this.orm.call("loyalty.program", "get_total_promo", {}),
        ]);
        // Update the state with the fetched parent data
        this.state.categoryList = ParentProduct.parent_product;
        this.state.selectedCategories = ParentList.parent_list;
        this.state.promo = TotalPromo.promotions;
        this.state.selectedPromo = PromoList.promotion_list;

    } catch (error) {
        console.error("Error fetching parent data", error);
    }
  }
}
OwlPosDashboard.template = "owl.OwlPosDashboard";
registry.category("actions").add("owl.pos_dashboard", OwlPosDashboard);