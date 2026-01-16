import discord
from discord import Role

import config
from config import RoleId
from database import divisions


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

    new_roles = [
        role for role in initial_roles if role.id not in other_division_role_ids
    ]

    if target_role_id and not any(role.id == target_role_id for role in new_roles):
        if initial_roles:
            guild = initial_roles[0].guild
            role = guild.get_role(target_role_id)
            if role:
                new_roles.append(role)

    return new_roles


def to_rank(initial_roles: list[discord.Role], rank: int | None) -> list[Role]:
    target_role_ids = set()
    if rank is not None:
        if rank >= 4:
            target_role_ids.add(RoleId.CONTRACT.value)
        target_role_ids.add(config.RANK_ROLES[config.RANKS[rank]])

    roles_to_remove = set(config.RANK_ROLES.values())
    roles_to_remove.add(RoleId.CONTRACT.value)

    new_roles = [role for role in initial_roles if role.id not in roles_to_remove]
    for role_id in target_role_ids:
        if not any(role.id == role_id for role in new_roles):
            if initial_roles:
                guild = initial_roles[0].guild
                role = guild.get_role(role_id)
                if role:
                    new_roles.append(role)

    return new_roles
