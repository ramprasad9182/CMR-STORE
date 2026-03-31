/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Order , Payment,Orderline} from "@point_of_sale/app/store/models";
import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(Order.prototype, {

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

   remove_paymentline(line) {
        this.assert_editable();
        if (this.selected_paymentline === line) {

            this.select_paymentline(undefined);
        }
        this.paymentlines.remove(line);
        line.order.credit_partner = false;
        line.order.credit_ids = line.order.credit_ids.filter(id => id !== line.credit_note_id);
        line.order.credit_note_amounts = line.order.credit_note_amounts.filter(amount => amount !== line.amount);
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
    let existing_amt = 0
    for (const line of this.paymentlines) {
    existing_amt += line.amount
    }
    if (partner && partner.id === order.credit_partner) {
        const total = order.get_total_with_tax() + order.get_rounding_applied();
        const redeem_amount = order.credit_note_amount || 0;
         const amt = total -  existing_amt
        credit_amount = Math.min(amt, redeem_amount);
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
                const newPaymentline = new Payment(
                    { env: this.env },
                    {
                        order: this,
                        payment_method: credit_method,
                        pos: this.pos,
                    }
                );
                newPaymentline.set_amount(credit_amount);
                this.credit_note_amounts = [
    ...(this.credit_note_amounts || []),
     credit_amount
];
                newPaymentline.set_credit_note(this.credit_id);
                this.paymentlines.add(newPaymentline);
                this.credit_partner = false;
        } else {
            await this.pos.env.services.popup.add(ErrorPopup, {
                title: _t("Missing Payment Method"),
                body: _t("Credit settlement method is not configured."),
            });
            return;
        }
    }

    // 5. Check for reward conflicts
//    const rewards = this._validGetPotentialRewards().filter(
//        ({ reward }) =>
//             (reward.discount_max_amount > 0 && reward.buy_with_reward_price ==='no') || reward.reward_type === 'discount'
//    );
//    if (rewards.length > 0) {
//        await this.env.services.popup.add(ErrorPopup, {
//            title: _t("Apply Rewards"),
//            body: _t("Please apply one reward before proceeding."),
//        });
//        return;
//    }

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
     _applyReward(reward, coupon_id, args) {

        // call parent logic first

        const result = super._applyReward(reward, coupon_id, args);



        if (result === true && reward.reward_type === "product") {

            const order = this.pos.get_order();



            // reward_product_id is Many2one -> [id, name]

            const rewardProductId = reward.reward_product_id?.[0];

            const rewardProductName = reward.reward_product_id?.[1];



            if (rewardProductId) {

                order.get_orderlines().forEach(line => {

                    if (line.product.id === rewardProductId) {

                        // tag this orderline for later serial validation

                        line.is_reward_line = true;

                        line.reward_id = reward.id;

                        line.reward_product_id = rewardProductId;

                        line.reward_product_name = rewardProductName;



                        console.log(

                            "Tagged reward orderline:",

                            rewardProductName,

                            "ID:", rewardProductId,

                            "Reward ID:", reward.id

                        );

                    }

                });

            } else {

                console.warn("reward_product_id not set on reward:", reward);

            }

        }

        else if (result === true && reward.reward_type === "discount_on_product") {

            const order = this.pos.get_order();



            // reward_product_id is Many2one -> [id, name]

            const rewardProductId = reward.discount_product_id?.[0];

            const rewardProductName = reward.discount_product_id?.[1];



            if (rewardProductId) {

                order.get_orderlines().forEach(line => {

                    if (line.product.id === rewardProductId) {

                        // tag this orderline for later serial validation

                        line.is_reward_line = true;

                        line.reward_id = reward.id;

                        line.reward_product_id = rewardProductId;

                        line.reward_product_name = rewardProductName;



                        console.log(

                            "Tagged reward orderline:",

                            rewardProductName,

                            "ID:", rewardProductId,

                            "Reward ID:", reward.id

                        );

                    }

                });

            } else {

                console.warn("reward_product_id not set on reward:", reward);

            }

        }



        return result;

    },
});

