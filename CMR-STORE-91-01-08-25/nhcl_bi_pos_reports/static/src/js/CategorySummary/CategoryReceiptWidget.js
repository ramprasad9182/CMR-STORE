/** @odoo-module */

import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";
import { XMLPosCategorySummaryReceipt } from "@nhcl_bi_pos_reports/js/CategorySummary/XMLPosCategorySummaryReceipt";
import { useService } from "@web/core/utils/hooks";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

export class CategoryReceiptWidget extends ReceiptScreen {
    static template = "nhcl_bi_pos_reports.CategoryReceiptWidget";
    static components = { XMLPosCategorySummaryReceipt }
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.printer = useService("printer");
    }

    back() {
        this.pos.closeTempScreen();
       	this.pos.showScreen('ProductScreen');
    }

	orderDone() {
		const { name, props } = this.nextScreen;
		this.showScreen(name, props);
	}

	async printReceipt() {
        this.buttonPrintReceipt.el.className = "fa fa-fw fa-spin fa-circle-o-notch";
        const isPrinted = await this.printer.print(
            XMLPosCategorySummaryReceipt,
            {
                data: this.pos.get_order().export_for_printing(),
                formatCurrency: this.env.utils.formatCurrency,
                order: this.get_category_receipt_data(),
            },
            { webPrintFallback: true }
        );

        if (isPrinted) {
            this.currentOrder._printed = true;
        }

        if (this.buttonPrintReceipt.el) {
            this.buttonPrintReceipt.el.className = "fa fa-print";
        }
    }
    
    get_category_receipt_data(){
		var self = this;
		var categ_current_session = this['props']['categ_current_session'];
		if(categ_current_session == true)
		{
			return {
				widget: this,
				pos: this.pos,
				categ_current_session : categ_current_session ,
				cate_summary: this.get_category_summery(),
				final_total:this.get_category_final_total(),
				date_c: (new Date()).toLocaleString()
			};
		}
		else{
			return {
				widget: this,
				pos: this.pos,
				categ_current_session : categ_current_session ,
				cate_summary: this.get_category_summery(),
				st_date_categ:this.get_category_st_date(),
				ed_date_categ:this.get_category_ed_date(),
				st_month_categ:this.get_category_st_month(),
				ed_month_categ:this.get_category_ed_month(),
				final_total:this.get_category_final_total(),
				date_c: (new Date()).toLocaleString()
			};
		}
		
	}

	get_category_summery(){ 
		return this['props']['category_summary']; 
	}

	get_category_st_date(){
		var st_date = this['props']['start_date_categ'].split("-")
		
		var st_date_d = st_date[2];
		var st_date_m = st_date[1];
		var st_date_y = st_date[0];
		var full_st_date = st_date_d+'-'+st_date_m+'-'+st_date_y
		return full_st_date; 
	}
	get_category_ed_date(){
		var ed_date = this['props']['end_date_categ'].split("-")

		var ed_date_d = ed_date[2];
		var ed_date_m = ed_date[1];
		var ed_date_y = ed_date[0];
		var full_ed_date = ed_date_d+'-'+ed_date_m+'-'+ed_date_y
		return full_ed_date;
	}

	get_category_st_month(){
		var st_date = this['props']['start_date_categ'].split("-")
		
		var monthNames = ["",
			"January", "February", "March",
			"April", "May", "June", "July",
			"August", "September", "October",
			"November", "December"
		];

		var st_date_m_index = st_date[1];
		var st_date_split = st_date_m_index.split('')
		
		if(st_date_split[0] > '0'){
			st_date_m_index = st_date_m_index
		}else{
			st_date_m_index = st_date_m_index.split('')[1]
		}
		var st_date_y = st_date[0];

		return monthNames[st_date_m_index]+'-'+st_date_y;
	}

	get_category_ed_month(){
		var ed_date = this['props']['end_date_categ'].split("-")

		var monthNames = ["",
			"January", "February", "March",
			"April", "May", "June", "July",
			"August", "September", "October",
			"November", "December"
		];

		var ed_date_m_index = ed_date[1];

		var ed_date_split = ed_date_m_index.split('')
		if(ed_date_split[0] > '0'){
			ed_date_m_index = ed_date_m_index
		}else{
			ed_date_m_index = ed_date_m_index.split('')[1]
		}
		var ed_date_y = ed_date[0];

		return monthNames[ed_date_m_index]+'-'+ed_date_y;
	}

	get_category_final_total(){ 
		return this['props']['final_total']; 
	}

	get category_receipt_data() {
		var self = this;
		var categ_current_session = this['props']['categ_current_session'];
		if(categ_current_session == true)
		{
			return {
				widget: this,
				pos: this.pos,
				categ_current_session : categ_current_session ,
				cate_summary: this.get_category_summery(),
				final_total:this.get_category_final_total(),
				date_c: (new Date()).toLocaleString()
			};
		}
		else{
			return {
				widget: this,
				pos: this.pos,
				categ_current_session : categ_current_session ,
				cate_summary: this.get_category_summery(),
				st_date_categ:this.get_category_st_date(),
				ed_date_categ:this.get_category_ed_date(),
				st_month_categ:this.get_category_st_month(),
				ed_month_categ:this.get_category_ed_month(),
				final_total:this.get_category_final_total(),
				date_c: (new Date()).toLocaleString()
			};
		}
		
	}

    
}

registry.category("pos_screens").add("CategoryReceiptWidget", CategoryReceiptWidget);