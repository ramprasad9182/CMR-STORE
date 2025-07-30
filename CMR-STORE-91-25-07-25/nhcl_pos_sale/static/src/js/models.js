/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Order , Payment,Orderline} from "@point_of_sale/app/store/models";
import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(Order.prototype, {

//    async add_product(product, options) {
//        if (
//            this.pos.doNotAllowRefundAndSales() &&
//            this._isRefundOrder() &&
//            (!options.quantity || options.quantity > 0)
//        ) {
//            this.pos.env.services.popup.add(ErrorPopup, {
//                title: _t("Refund and Sales not allowed"),
//                body: _t("It is not allowed to mix refunds and sales"),
//            });
//            return;
//        }
//        if (this._printed) {
//            // when adding product with a barcode while being in receipt screen
//            this.pos.removeOrder(this);
//            return await this.pos.add_new_order().add_product(product, options);
//        }
//        this.assert_editable();
//        options = options || {};
//        const quantity = options.quantity ? options.quantity : 1;
//        const line = new Orderline(
//            { env: this.env },
//            { pos: this.pos, order: this, product: product, quantity: quantity }
//        );
//        this.fix_tax_included_price(line);
//
//        this.set_orderline_options(line, options);
//        line.set_full_product_name();
//        var to_merge_orderline;
//        for (var i = 0; i < this.orderlines.length; i++) {
//            if (this.orderlines.at(i).can_be_merged_with(line) && options.merge !== false) {
//                to_merge_orderline = this.orderlines.at(i);
//            }
//        }
//        if (to_merge_orderline) {
//            to_merge_orderline.merge(line);
//            this.select_orderline(to_merge_orderline);
//        } else {
//            this.add_orderline(line);
//            this.select_orderline(this.get_last_orderline());
//        }
//        if (options.draftPackLotLines) {
//
//            this.selected_orderline.setPackLotLines({
//                ...options.draftPackLotLines,
//                setQuantity: options.quantity === undefined,
//            });
//        }
//
//          if (
//        (product.tracking === 'serial' || product.tracking === 'lot') &&
//       (!options?.draftPackLotLines?.lines || options.draftPackLotLines.lines.length === 0)
//    ) {
//       const order = this.pos.get_order()
//       if(line.pack_lot_lines.length == 0){
//
//
//            order._unlinkOrderline(line)
//
//            return
//
//       }
//    }
//        if (options.comboLines?.length) {
//            await this.addComboLines(line, options);
//            // Make sure the combo parent is selected.
//            this.select_orderline(line);
//        }
//        this.hasJustAddedProduct = true;
//        clearTimeout(this.productReminderTimeout);
//        this.productReminderTimeout = setTimeout(() => {
//            this.hasJustAddedProduct = false;
//        }, 3000);
//        return line;
//    },


    _mergeFreeProductRewards(freeProductRewards, potentialFreeProductRewards) {
        const result = [];
        for (const reward of potentialFreeProductRewards) {
            if (!freeProductRewards.find((item) => item.reward.id === reward.reward.id)) {
                result.push(reward);
            }
        }
        return freeProductRewards.concat(result);
    },



   _validGetPotentialRewards() {
        const order = this.pos.get_order();
         const rewardLines = order.get_orderlines()
        .filter(line => line.is_reward_line)
        .map(line => {
            const reward = this.pos.reward_by_id[line.reward_id];
            return reward ? reward.program_id.id : null;
        })
        .filter(programId => programId !== null);

        let rewards = [];
        if (order) {
            const claimableRewards = order.getClaimableRewards();
            rewards = claimableRewards.filter(
                ({ reward }) => reward.program_id.program_type !== "ewallet"  &&
                !rewardLines.includes(reward.program_id.id)
            );
        }
        const discountRewards = rewards.filter(({ reward }) => reward.reward_type == "discount");
        const freeProductRewards = rewards.filter(({ reward }) => reward.reward_type == "product");
        const potentialFreeProductRewards = this.pos.getPotentialFreeProductRewards();
   return discountRewards.concat(
        this._mergeFreeProductRewards(freeProductRewards, potentialFreeProductRewards)
    );
    },
async pay() {
    const order = this.pos.get_order();

    // 1. Ensure customer is selected
    if (!order || !order.get_partner()) {
        await this.pos.env.services.popup.add(ErrorPopup, {
            title: _t("Customer Not Giving"),
            body: _t("Please add a customer and try again"),
        });
        return false;
    }

    // 2. Prevent zero-quantity products
    const filteredOrderLines = this.get_orderlines().filter((line) => line.quantity === 0);
    if (filteredOrderLines.length > 0) {
        await this.pos.env.services.popup.add(ErrorPopup, {
            title: _t("Zero Quantity Not Allowed"),
            body: _t("Product with Zero Quantity not allowed"),
        });
        return;
    }

    // 3. Setup credit application
    const partner = this.get_partner();
    let credit_amount = 0;


    this.paymentlines.forEach(line => {
                        this.paymentlines.remove(line);
                     })

    if (partner && partner.id === order.credit_partner) {
        const total = order.get_total_with_tax() + order.get_rounding_applied();
        const redeem_amount = order.credit_note_amount || 0;

        credit_amount = Math.min(total, redeem_amount);
    }

    // 4. Apply credit payment line
    if (partner && credit_amount > 0) {
        const credit_methods = this.pos.payment_methods.filter(
            (method) =>
                method.is_credit_settlement === true &&
                this.pos.config.payment_method_ids.includes(method.id)
        );

        if (credit_methods.length > 0) {
            const credit_method = credit_methods[0];

            const existingPaymentLine = this.paymentlines.find(
                (line) => line.payment_method.id === credit_method.id
            );

            if (!existingPaymentLine) {
                const newPaymentline = new Payment(
                    { env: this.env },
                    {
                        order: this,
                        payment_method: credit_method,
                        pos: this.pos,
                    }
                );
                newPaymentline.set_amount(credit_amount);
                this.paymentlines.add(newPaymentline);
            } else {
                // Update amount if already exists
                existingPaymentLine.set_amount(credit_amount);
            }
        } else {
            await this.pos.env.services.popup.add(ErrorPopup, {
                title: _t("Missing Payment Method"),
                body: _t("Credit settlement method is not configured."),
            });
            return;
        }
    }

    // 5. Check for reward conflicts
    const rewards = this._validGetPotentialRewards().filter(
        ({ reward }) =>
            reward.discount_max_amount > 0 || reward.reward_type === 'product'
    );

    if (rewards.length > 1) {
        await this.env.services.popup.add(ErrorPopup, {
            title: _t("Apply Rewards"),
            body: _t("Please apply one reward before proceeding."),
        });
        return;
    }

    // 6. Proceed with default payment flow
    super.pay();
},
    remove_auto_promolines(rewardlines){
    for (var rewardline of rewardlines){
    const reward = this.pos.reward_by_id[rewardline.reward_id];
          if (reward.discount_applicability != 'order'){
            for (var promodiscline of rewardline.promodisclines) {
            if (promodiscline) {
                var remove_line = this.get_orderlines().find(
            (line) => line.cid === promodiscline);
            remove_line.promo = 0;

            } else {
              continue;
            }
        }

}

    }

    },

     _resetPrograms() {
        this.disabledRewards = new Set();
        this.codeActivatedProgramRules = [];
        this.codeActivatedCoupons = [];
        this.couponPointChanges = {};
        this.remove_auto_promolines(this._get_reward_lines())
        this.orderlines.remove(this._get_reward_lines());
        this._updateRewards();
    },
});

