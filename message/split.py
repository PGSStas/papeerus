from datetime import datetime
import random


class Split:
    def splitId(self, message: str):
        id = ""
        mes = ""
        kol = 0
        for ch in message:
            if ch == '\0' and kol == 0:
                kol = 1
                continue
            if kol == 0:
                id += ch
            else:
                mes += ch
        return int(id), mes

    def split(self, message: str):
        ans = [""]
        head = ""
        tek = ""
        count = 0
        id = random.getrandbits(64)
        for i in message:
            tek += i
            if len(tek) >= 100:
                ans.append(str(id) + '\0' + str(count) + '\0' + tek)
                tek = ""
                count += 1
        ans.append(str(id) + '\0' + str(count) + '\0' + tek)
        tek = ""
        count += 1
        now = datetime.now()
        date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
        ans[0] = str(id) + '\0' + '\0' + str(count) + '\0' + date_time
        # print(ans)
        return ans

    def construct(self, message: list):
        ans = ""
        map = {}
        for i in message:
            if i[0] == '\0':
                continue
            first = ""
            second = ""
            ok = False
            for j in i:
                if j == '\0' and ok == False:
                    ok = True
                    continue
                if ok:
                    second += j
                else:
                    first += j
            map[int(first)] = second
        for i in map.values():
            ans += i
        return ans
