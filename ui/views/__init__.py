from .dismissal import (
    DismissalApplyView,
    DismissalCancelButton,
    DismissalManagementButton,
)
from .reinstatement import (
    ApproveReinstatementButton,
    ReinstatementApplyView,
    ReinstatementRankSelect,
    RejectReinstatementButton,
)
from .role_getting import ApproveRoleButton, RejectRoleButton, RoleApplyView
from .supplies import SupplyCreateView, SupplyManageButton
from .supplies_audit import SupplyAuditView
from .transfers import (
    ApproveTransferButton,
    OldApproveButton,
    RejectTransferButton,
    TransferApply,
)
from .transfers import (
    TransferView as TransferView,
)


def load_persistent_views(bot):
    bot.add_view(ReinstatementApplyView())
    bot.add_view(RoleApplyView())
    bot.add_view(SupplyCreateView())
    bot.add_view(SupplyAuditView())
    bot.add_view(DismissalApplyView())


def load_buttons(bot):
    bot.add_dynamic_items(
        ApproveReinstatementButton,
        ReinstatementRankSelect,
        RejectReinstatementButton,
        ApproveRoleButton,
        RejectRoleButton,
        SupplyManageButton,
        DismissalManagementButton,
        DismissalCancelButton,
        TransferApply,
        ApproveTransferButton,
        RejectTransferButton,
        OldApproveButton,
    )
    load_persistent_views(bot)
