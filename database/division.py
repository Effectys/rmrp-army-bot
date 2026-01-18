from typing import Tuple

import discord

from database.models import Division, Position


class Divisions:
    def __init__(self):
        self.divisions: list[Division] = []
        self._by_id: dict[int, Division] = {}
        self._by_abbr: dict[str, Division] = {}

    async def load(self):
        self.divisions = await Division.find_all().to_list()
        self._rebuild_cache()

    def _rebuild_cache(self):
        """Перестроить кэш после загрузки данных"""
        self._by_id = {d.division_id: d for d in self.divisions}
        self._by_abbr = {d.abbreviation.lower(): d for d in self.divisions}

    def get_division(self, division_id: int) -> Division | None:
        """O(1) поиск по ID"""
        return self._by_id.get(division_id)

    def get_division_by_abbreviation(self, abbreviation: str) -> Division | None:
        """O(1) поиск по аббревиатуре (регистронезависимый)"""
        return self._by_abbr.get(abbreviation.lower())

    def get_division_name(self, division_id: int) -> str | None:
        """Получить имя подразделения по ID"""
        div = self._by_id.get(division_id)
        return div.name if div else None

    def get_user_data(self, user: discord.Member) -> Tuple[Division | None, Position | None]:
        """Получить подразделение и должность пользователя из его ролей"""
        user_role_ids = {role.id for role in user.roles}

        for div in self.divisions:
            for pos in div.positions:
                if pos.role_id in user_role_ids:
                    return div, pos

        for div in self.divisions:
            if div.role_id in user_role_ids:
                return div, None

        return None, None