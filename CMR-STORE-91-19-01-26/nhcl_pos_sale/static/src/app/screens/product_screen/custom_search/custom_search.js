/** @odoo-module **/
import { Component, useState, useEffect, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";


export class CustomSearch extends Component {
   static components = { Input };

    static template = "nhcl_pos_sale.CustomSearch";
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.barcodeReader = useService("barcode_reader");
        this.orm = useService("orm");

       }

//     async onClick(){
//
//    this.barcodeReader.scan(this.pos.searchProductByCode.trim())
//
//   }

async handleKeyDown(event) {
    if (event.key === 'Enter') {
        event.preventDefault(); // Prevent default behavior if needed

        this.showLoadingIndicator = true; // Show loading indicator

        try {
            const inputValue = event.target.value.trim();

           if (inputValue.toLowerCase().startsWith("r")) {
                  const formattedValue = "R" + inputValue.slice(1);
              const domain = [['name', '=', formattedValue]];


                const get_all_serials = await this.orm.call('stock.lot', 'search_read', [domain]);
                const search_serial  = get_all_serials[0]
//                const search_serial = get_all_serials.find(serial => serial.name === inputValue);

                if (search_serial) {
                    const domain = [['id', '=', search_serial.product_id[0]]];
                    const prod_bar = await this.orm.call('product.product', 'search_read', [domain]);
                    this.barcodeReader.scan(`01${prod_bar[0].barcode}21${formattedValue}`);
                }

                else {
                this.barcodeReader.scan(formattedValue);
            }



            }




            else {
                this.barcodeReader.scan(inputValue);
            }

            event.target.value = "";
            this.pos.searchProductByCode = "";
            event.target.blur();
        } catch (error) {
            console.error('Error processing:', error);
        } finally {
            this.showLoadingIndicator = false; // Hide loading indicator
        }
    }
}


    }