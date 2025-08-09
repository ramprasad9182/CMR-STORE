
/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { RewardButton } from "@pos_loyalty/app/control_buttons/reward_button/reward_button";
patch(RewardButton.prototype, {
     _getPotentialRewards() {
        const order = this.pos.get_order();
         const rewardLines = order.get_orderlines()
        .filter(line => line.is_reward_line) // Filter for reward lines
        .map(line => {
            const reward = this.pos.reward_by_id[line.reward_id]; // Get the reward by its ID
            return reward ? reward.program_id.id : null; // Return the program_id or null if not found
        })
        .filter(programId => programId !== null);
        // Claimable rewards excluding those from eWallet programs.
        // eWallet rewards are handled in the eWalletButton.
        let rewards = [];
        if (order) {
            const claimableRewards = order.getClaimableRewards();
            rewards = claimableRewards.filter(
                ({ reward }) => reward.program_id.program_type !== "ewallet"  &&
                !rewardLines.includes(reward.program_id.id)
            );
        }
//        const discountRewards = [];
        const discountRewards = rewards.filter(({ reward }) => reward.reward_type == "discount");
        const freeProductRewards = rewards.filter(({ reward }) => reward.reward_type == "product");
        const potentialFreeProductRewards = this.pos.getPotentialFreeProductRewards();
   return discountRewards.concat(
        this._mergeFreeProductRewards(freeProductRewards, potentialFreeProductRewards)
    );
    },
         hasClaimableRewards() {
                    const order = this.pos.get_order();
        if (this._getPotentialRewards().length > 0){
        if (this._getPotentialRewards().filter(({ reward }) => reward.reward_type=== "product").length>0){
         order.is_rew = true;
        }
        else{
         order.is_rew = false;
        }
                this.auto_apply_rewards()
        }
        else {
        order.is_rew = false;
        }
//        return this._getPotentialRewards().filter(({ reward }) => reward.reward_type=== "product").length>0;
        return this._getPotentialRewards().length > 0;
    },
       async click() {
//        const rewards = this._getPotentialRewards();
const rewards = this._getPotentialRewards().filter(({ reward }) => reward.discount_max_amount > 0 || reward.reward_type == 'product');          if (rewards.length >= 1) {
            const rewardsList = rewards.reduce((acc, reward) => {
            const programId = reward.reward.program_id.id;
            if (!acc[programId]) {
            acc[programId] = [];
            }
            acc[programId].push(reward);
            return acc;
            }, {});

            console.log("dd",rewardsList)
            const highestDiscountRewards = Object.values(rewardsList).map((programRewards) => {
            const maxDiscountReward = programRewards.reduce((max, current) => {
            if(current.reward.discount_max_amount > 0){

             return   current.reward.discount_max_amount > max.reward.discount_max_amount ? current : max;

            }

            return current.reward.discount > max.reward.discount ? current : max; // Assuming `discount` exists
            });
            return {
            id: maxDiscountReward.reward.id,
            label: maxDiscountReward.reward.description,
            description: maxDiscountReward.reward.program_id.name,
            item: maxDiscountReward,
            };
            });
            console.log("highestDiscountRewards",highestDiscountRewards)
//            highestDiscountRewards_lst = highestDiscountRewards.filter(({ reward }) => reward.reward_type=== "product")
            const { confirmed, payload: selectedReward } = await this.popup.add(SelectionPopup, {
                title: _t("Please select a reward"),
                list: highestDiscountRewards,
            });
            if (confirmed) {
                return this._applyReward(
                    selectedReward.reward,
                    selectedReward.coupon_id,
                    selectedReward.potentialQty
                );
            }
        }
        return false;
    },
         auto_apply_rewards() {
      let order=this.pos.get_order();
        const rewards = this._getPotentialRewards();
         const rewardsList = rewards.reduce((acc, reward) => {
            const programId = reward.reward.program_id.id;
            if (!acc[programId]) {
            acc[programId] = [];
            }
            acc[programId].push(reward);
            return acc;
            }, {});
            const highestDiscountRewards = Object.values(rewardsList).map((programRewards) => {



           const filteredRewards = programRewards.filter(reward => !reward.reward.discount_max_amount || reward.reward.discount_max_amount <= 0);
              console.log("filtered",filteredRewards)
        if (filteredRewards.length === 0) return null; // If no valid rewards, return null

        const maxDiscountReward = filteredRewards.reduce((max, current) => {
            return current.reward.discount > max.reward.discount ? current : max;
        });
            return {
            id: maxDiscountReward.reward.id,
            label: maxDiscountReward.reward.description,
            description: maxDiscountReward.reward.program_id.name,
            item: maxDiscountReward,
            };
            }).filter(item => item !== null);

            console.log("highest",highestDiscountRewards)
            for (var i = 0, l = highestDiscountRewards.length; i < l; ++i) {
            let reward = highestDiscountRewards[i]['item']['reward']
            let coupon_id = highestDiscountRewards[i]['item']['coupon_id']
            let potentialQty = highestDiscountRewards[i]['item']['potentialQty']
             order._applyReward(reward, coupon_id);
                }
      }
})