# Zadanie Praktyczne

Wykonali: **Seratowicz Łukasz, Czajkowski Tomasz**

Link do Prezentacji: ***https://docs.google.com/presentation/d/1PrZCXZiF48XxDs-BcrGoxy5CqKCiTC4eQqFX99rpzBI/edit?usp=sharing***

## Pomocne linki
Pycord docs ***https://docs.pycord.dev/en/stable/***.<br>
Fandom API ***https://pypi.org/project/fandom-py/***.<br>
Przykłady ***https://github.com/Pycord-Development/pycord/tree/master/examples/app_commands***.

## Przed przystąpieniem do zadań (setup)
Jeżeli jeszcze tego nie zrobiliście, należy dołączyć na serwer ***DISCORD***: ***https://discord.gg/uNeEbM4J***<br>
Po otrzymaniu roli od nas, powinniście widzieć własny kanał o nazwie numeru waszego bota. Na waszym kanale jest podany token bota.<br>

Należy zainstalować plik [DiscordBotTemplate.zip](https://github.com/malpkakefirek/MCPedia/blob/main/DiscordBotTemplate.zip), rozpakować i otworzyć folder w swoim ulubionym IDE pythona.<br>

Następnie w pliku `config.json` należy podać informacje o bocie, w tym token który znajduje się na twoim kanale.<br>

Należy zainstalować biblioteki poniższymi komendami:<br>
`pip install py-cord`<br>
`pip install fandom-py`<br>

Jeżeli masz zainstalowany `discord.py` *mogą* wystąpić pewne problemy. Aby odinstalować, należy wpisać poniższą komendę:<br>
`pip uninstall discord.py`<br>

Uruchamia się bota, poprzez uruchomienie pliku `main.py`. Możesz to zrobić przez IDE, lub z wiersza poleceń: `python3 main.py`<br>

W folderze `cogs/` znajdują się cogi bota.<br>
**Na potrzeby zadań będziecie jedynie edytować plik** `cogs/template_cog.py`:exclamation:<br>

Komendy próbujcie jedynie na swoich kanałach:exclamation:<br>

## Zadania

---

#### 1. Zadanie 1: [Pierwsze kroki]
> Włącz bota, który został ci przydzielony. (Nie zapomnij zmodyfikować `config.json`)<br>
> Przetestuj komende `/hello` z pliku `cogs/template_cog.py` <br>
> Zmodyfikuj program by zwracał "Witaj adminie :wave:" jezeli nasza podawana nazwa to "admin", <br>
> a w przeciwnym przypadku wypisz "Witaj {name}!" <br>
---

#### 2. Zadanie 2: [Komenda Sum]
> Utwórz nową komendę, która przyjmuje 2 zmienne typu `int` - `x` i `y` <br>
> zmienna `x` ma byc wymagana. Zmienna `y` opcjonalna. <br>
> Jeżeli `y` nie istnieje: <br>
> Odpowiedz uzytkownikowi {"Podales tylko {x}"} <br>
> Jezeli `y` istnieje: <br>
> Odpowiedz użytkownikowi {"x={x}"} i w nowej linii: {"y={y}"}, a następnie wyślij osobną wiadomość {"{x} + {y} = {x+y}"} <br>
---

#### 3. Zadanie 3: [Embed]
> Utwórz nową komendę o nazwie "embed", która będzie przyjmowała dwie zmienne: <br>
> `title` typu `str`, wymagana <br>
> `message` typu `str`, wymagana <br>
> Komenda wyśle embed z tytułem `title`, contentem `message` i niebieskim kolorem <br>
> Note: pomocne może być: <br>
> ***https://docs.pycord.dev/en/stable/api/data_classes.html#discord.Embed*** <br>
> ***https://docs.pycord.dev/en/stable/api/data_classes.html#discord.Colour.blue*** <br>
---

#### 4. Zadanie 4: [Implementacja Miencraft Wiki]
> Utwórz nową komendę o nazwie "Summary", która po wpisaniu `/summary {input}`: <br>
> Odpowie na naszą komendę: <br>
> {Title} <br>
> {Summary} <br>
> Ustaw `input` jako wartość wymaganą. Sprawdź co zwraca Wiki jeżeli nie znajdzie żadnej strony, po czym zaimplementuj ochrone przed tym, która napisze użytkownikowi, że owa strona nie istnieje. <br>
> Skorzystaj w ciekawy sposób z Embed by urozmaicić wygląd naszej odpowiedzi. <br>
> **Note**: użyj `await ctx.defer()` na początku komendy. Jeżeli nie wiesz jak, możesz zapytać się prowadzących. <br>

---
