import discord
from discord import Role

import config
from config import RoleId
from database import divisions


def _apply_role_changes(
    initial_roles: list[discord.Role],
    roles_to_remove: set[int],
    target_role_ids: set[int],
) -> list[Role]:
    new_roles = [role for role in initial_roles if role.id not in roles_to_remove]

    for role_id in target_role_ids:
        if not any(role.id == role_id for role in new_roles):
            if initial_roles:
                guild = initial_roles[0].guild
                role = guild.get_role(role_id)
                if role:
                    new_roles.append(role)

    return new_roles


def to_division(
    initial_roles: list[discord.Role], division_id: int | None
) -> list[Role]:
    target_role_id = None
    other_division_role_ids = set()

    for division in divisions.divisions:
        if division.division_id == division_id:
            target_role_id = division.role_id
        else:
            other_division_role_ids.add(division.role_id)

    target_ids = {target_role_id} if target_role_id else set()
    return _apply_role_changes(initial_roles, other_division_role_ids, target_ids)


def to_rank(initial_roles: list[discord.Role], rank: int | None) -> list[Role]:
    target_role_ids = set()

    if rank is not None:
        target_role_ids.add(RoleId.MILITARY.value)
        if rank >= 4:
            target_role_ids.add(RoleId.CONTRACT.value)
        if rank == config.RankIndex.MAJOR:
            target_role_ids.update([RoleId.BRIGADE_HQ.value, RoleId.UNIT_DEPUTY_COMMANDER.value])
        if rank >= config.RankIndex.LIEUTENANT_COLONEL:
            target_role_ids.update([RoleId.BRIGADE_HQ.value, RoleId.GENERAL_HQ.value, RoleId.UNIT_COMMANDER.value])
        target_role_ids.add(config.RANK_ROLES[config.RANKS[rank]])

    roles_to_remove = set(config.RANK_ROLES.values())
    roles_to_remove.add(RoleId.CONTRACT.value)
    roles_to_remove.add(RoleId.MILITARY.value)

    return _apply_role_changes(initial_roles, roles_to_remove, target_role_ids)


def to_position(
    initial_roles: list[discord.Role],
    division_id: int | None,
    position_name: str | None,
) -> list[Role]:
    all_position_role_ids = set()
    target_role_id = None

    for division in divisions.divisions:
        if division.positions:
            for pos in division.positions:
                all_position_role_ids.add(pos.role_id)
                if division.division_id == division_id and pos.name == position_name:
                    target_role_id = pos.role_id

    target_ids = {target_role_id} if target_role_id else set()
    return _apply_role_changes(initial_roles, all_position_role_ids, target_ids)


def get_rank_from_roles(roles: list[discord.Role]) -> int | None:
    role_ids = {role.id for role in roles}

    for rank, role_id in config.RANK_ROLES.items():
        if role_id in role_ids:
            for rank_num, rank_name in enumerate(config.RANKS):
                if rank_name == rank:
                    return rank_num
    return None
