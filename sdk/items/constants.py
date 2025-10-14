class BallType:
	POKE_BALL = "poke-ball"
	GREAT_BALL = "great-ball"
	ULTRA_BALL = "ultra-ball"
	MASTER_BALL = "master-ball"
	SAFARI_BALL = "safari-ball"
	LEVEL_BALL = "level-ball"
	LURE_BALL = "lure-ball"
	MOON_BALL = "moon-ball"
	FRIEND_BALL = "friend-ball"
	LOVE_BALL = "love-ball"
	HEAVY_BALL = "heavy-ball"
	FAST_BALL = "fast-ball"
	SPORT_BALL = "sport-ball"
	NET_BALL = "net-ball"
	DIVE_BALL = "dive-ball"
	NEST_BALL = "nest-ball"
	REPEAT_BALL = "repeat-ball"
	TIMER_BALL = "timer-ball"
	LUXURY_BALL = "luxury-ball"
	PREMIER_BALL = "premier-ball"
	DUSK_BALL = "dusk-ball"
	HEAL_BALL = "heal-ball"
	QUICK_BALL = "quick-ball"
	CHERISH_BALL = "cherish-ball"

BALL_DATA = {
	BallType.POKE_BALL: {
		"name": "Poké Ball",
		"emoji": "<:pokeball:1424443006626431109>",
		"base_modifier": 1.0,
		"description": "Bola padrão para capturar Pokémon"
	},
	BallType.GREAT_BALL: {
		"name": "Great Ball",
		"emoji": "<:greatball:1424443251158552681>",
		"base_modifier": 1.5,
		"description": "Melhor que a Poké Ball padrão"
	},
	BallType.ULTRA_BALL: {
		"name": "Ultra Ball",
		"emoji": "<:ultraball:1424443441894658152>",
		"base_modifier": 2.0,
		"description": "Taxa de captura muito alta"
	},
	BallType.MASTER_BALL: {
		"name": "Master Ball",
		"emoji": "<:masterball:1424443734581317758>",
		"base_modifier": 255.0,
		"description": "Captura garantida"
	},
	BallType.SAFARI_BALL: {
		"name": "Safari Ball",
		"emoji": "<:safariball:1424443883357605938>",
		"base_modifier": 1.5,
		"description": "Usada no Safari Zone"
	},
	BallType.NET_BALL: {
		"name": "Net Ball",
		"emoji": "<:netball:1424444016505655366>",
		"base_modifier": 1.0,
		"special": "bug_water",
		"description": "3x efetiva contra Bug e Water"
	},
	BallType.NEST_BALL: {
		"name": "Nest Ball",
		"emoji": "<:nestball:1424444161570111709>",
		"base_modifier": 1.0,
		"special": "low_level",
		"description": "Melhor contra Pokémon de nível baixo"
	},
	BallType.REPEAT_BALL: {
		"name": "Repeat Ball",
		"emoji": "<:repeatball:1424444375315906660>",
		"base_modifier": 1.0,
		"special": "caught_before",
		"description": "3x se já capturou essa espécie"
	},
	BallType.TIMER_BALL: {
		"name": "Timer Ball",
		"emoji": "<:timerball:1424444622712606882>",
		"base_modifier": 1.0,
		"special": "turn_based",
		"description": "Melhor quanto mais turnos passarem"
	},
	BallType.LUXURY_BALL: {
		"name": "Luxury Ball",
		"emoji": "<:luxuryball:1424444827977650279>",
		"base_modifier": 1.0,
		"description": "Taxa normal, mas aumenta amizade"
	},
	BallType.DIVE_BALL: {
		"name": "Dive Ball",
		"emoji": "<:diveball:1424483343881474191>",
		"base_modifier": 1.0,
		"special": "underwater",
		"description": "3.5x efetiva contra Pokémon subaquáticos"
	},
	BallType.PREMIER_BALL: {
		"name": "Premier Ball",
		"emoji": "<:premierball:1424444987638022185>",
		"base_modifier": 1.0,
		"description": "Taxa igual à Poké Ball"
	}
}

CATEGORY_NAMES = {
	"items": "Itens",
	"pokeballs": "Poké Balls",
	"berries": "Berries",
	"tms_hms": "TMs & HMs",
	"key_items": "Itens Chave"
}

ITEM_EMOJIS = {
	# Poké Balls
	"poke-ball": BALL_DATA.get("poke-ball").get("emoji"),
	"great-ball": BALL_DATA.get("great-ball").get("emoji"),
	"ultra-ball": BALL_DATA.get("ultra-ball").get("emoji"),
	"master-ball": BALL_DATA.get("master-ball").get("emoji"),
	"safari-ball": BALL_DATA.get("safari-ball").get("emoji"),
	"net-ball": BALL_DATA.get("net-ball").get("emoji"),
	"nest-ball": BALL_DATA.get("nest-ball").get("emoji"),
	"repeat-ball": BALL_DATA.get("repeat-ball").get("emoji"),
	"timer-ball": BALL_DATA.get("timer-ball").get("emoji"),
	"luxury-ball": BALL_DATA.get("luxury-ball").get("emoji"),
	"dive-ball": BALL_DATA.get("dive-ball").get("emoji"),
	"premier-ball": BALL_DATA.get("premier-ball").get("emoji"),

	# Healing Items
	"potion": "<:potion:1424449023900778549>",
	"super-potion": "<:superpotion:1424449247734141071>",
	"hyper-potion": "<:hyperpotion:1424449418483994795>",
	"max-potion": "<:maxpotion:1424449757417439355>",
	"full-restore": "<:fullrestore:1424449940620574751>",
	"revive": "<:revive:1424450097135226910>",
	"max-revive": "<:maxrevive:1424450265423020144>",

	# Drinks/Consumable
	"fresh-water": "<:freshwater:1424451044649209856>",
	"soda-pop": "<:sodapop:1424451187549409440>",
	"lemonade": "<:lemonade:1424451357208871052>",
	"moomoo-milk": "<:moomoomilk:1424451527275450513>",
	"berry-juice": "<:berryjuice:1424451844402450564>",
	"rare-candy": "<:rarecandy:1424490496893653162>",

	# Herbal Medicine
	"energy-powder": "<:energypowder:1424453803490410578>",
	"energy-root": "<:energyroot:1424454053693358192>",
	"heal-powder": "<:healpowder:1424454225659822101>",
	"revival-herb": "<:revivalherb:1424454521828016250>",

	# Status Healer
	"antidote": "<:antidote:1424454872333418496>",
	"paralyze-heal": "<:paralyzeheal:1424456268009177239>",
	"awakening": "<:awakening:1424455117616451755>",
	"burn-heal": "<:burnheal:1424456539732836452>",
	"ice-heal": "<:iceheal:1424456708021030933>",
	"full-heal": "<:fullheal:1424456856780410972>",
	"lava-cookie": "<:lavacookie:1424457033188380824>",

	# Vitamins
	"hp-up": "<:hpup:1424457833549660422>",
	"protein": "<:protein:1424457974671212584>",
	"iron": "<:iron:1424458274417278997>",
	"carbos": "<:carbos:1424458453929296074>",
	"calcium": "<:calcium:1424458635173433446>",
	"zinc": "<:zinc:1424458781386870920>",

	# PP Restoration
	"ether": "<:ether:1424459097117429781>",
	"max-ether": "<:maxether:1424459222921252925>",
	"elixir": "<:elixir:1424459407604977910>",
	"max-elixir": "<:maxelixir:1424459559384125561>",
	"pp-up": "<:ppup:1424459749692407980>",
	"pp-max": "<:ppmax:1424459889153015848>",

	# Evolution Stones
	"fire-stone": "<:firestone:1424460341491798146>",
	"water-stone": "<:waterstone:1424460587152441494>",
	"thunder-stone": "<:thunderstone:1424460779415011348>",
	"leaf-stone": "<:leafstone:1424460948084621472>",
	"moon-stone": "<:moonstone:1424461085444018198>",
	"sun-stone": "<:sunstone:1424461237642727618>",

	# Battle Items
	"x-attack": "<:xattack:1424461484079190097>",
	"x-defense": "<:xdefense:1424461718322413638>",
	"x-speed": "<:xspeed:1424461900078383346>",
	"x-accuracy": "<:xaccuracy:1424462079879938219>",
	"x-sp-atk": "<:xspatk:1424463706938408971>",
	"x-sp-def": "<:xspdef:1424463936337740000>",
	"dire-hit": "<:direhit:1424462882623455333>",
	"guard-spec": "<:guardspec:1424463034780356688>",

	# Repels
	"repel": "<:repel:1424464410054758532>",
	"super-repel": "<:superrepel:1424464493345505330>",
	"max-repel": "<:maxrepel:1424464572353347694>",

	# Escape Items
	"escape-rope": "<:escaperope:1424464766633513051>",
	"poke-doll": "<:pokedoll:1424464908694851646>",
	"fluffy-tail": "<:fluffytail:1424465071274463276>",

	# Flutes
	"blue-flute": "<:blueflute:1424465825267585104>",
	"yellow-flute": "<:yellowflute:1424465964615073844>",
	"red-flute": "<:redflute:1424466105476579529>",
	"black-flute": "<:blackflute:1424466279456178176>",
	"white-flute": "<:whiteflute:1424466420162625608>",

	# Rods
	"old-rod": "<:oldrod:1424511581332439125>",
	"good-rod": "<:goodrod:1424511639108976671>",
	"super-rod": "<:superrod:1424511686198558770>",

	# Plot Advancement
	"ss-ticket": "<:ssticket:1424511801785319435>",
	"devon-parts": "<:devonparts:1424512364199411745>",
	"basement-key": "<:basementkey:1424512723609325570>",
	"poke-flute": "<:pokeflute:1424513239588274296>",
	"oaks-parcel": "<:oaksparcel:1424631876961697803>",
	"bike-voucher": "<:bikevoucher:1424521731376287829>",
	"gold-teeth": "<:goldteeth:1424521855745921065>",
	"card-key": "<:cardkey:1424522004509364346>",
	"lift-key": "<:liftkey:1424522116824563723>",
	"silph-scope": "<:silphscope:1424522233916817551>",
	"tri-pass": "<:tripass:1424523180785275071>",
	"rainbow-pass": "<:rainbowpass:1424523284992491571>",
	"tea": "<:tea:1424523355733889168>",
	"ruby": "<:ruby:1424524012230279259>",
	"sapphire": "<:sapphire:1424524024066609265>",
	"magma-emblem": "<:magmaemblem:1424524148243300486>",
	"letter": "<:letter:1424524945093824635>",
	"red-orb": "<:redorb:1424525143438524506>",
	"blue-orb": "<:blueorb:1424525150644207699>",
	"scanner": "<:scanner:1424525425853468832>",
	"meteorite": "<:meteorite:1424525662873456711>",
	"key-to-room-1": "<:keytoroom1:1424525898660577364>",
	"key-to-room-2": "<:keytoroom2:1424525946353881208>",
	"key-to-room-4": "<:keytoroom4:1424526912499355692>",
	"key-to-room-6": "<:keytoroom6:1424527084679729262>",

	# Event Items
	"secret-key": "<:secretkey:1424521556960215172>",
	"mysticticket": "<:mysticticket:1424523682642006156>",
	"auroraticket": "<:auroraticket:1424523756621266996>",
	"old-sea-map": "<:oldseamap:1424524290891583700>",
	"eon-ticket": "<:eonticket:1424525057400508540>",

	# Gameplay
	"contest-pass": "<:contestpass:1424512119579086848>",
	"wailmer-pail": "<:wailmerpail:1424512221156737177>",
	"soot-sack": "<:sootsack:1424512598749085897>",
	"bicycle": "<:bicycle:1424522357980004402>",
	"mach-bike": "<:machbike:1424511109406396516>",
	"acro-bike": "<:acrobike:1424512808875331648>",
	"coin-case": "<:coincase:1424511221666943097>",
	"dowsing-machine": "<:dowsingmachine:1424511453502640158>",
	"town-map": "<:townmap:1424522474074144932>",
	"vs-seeker": "<:vsseeker:1424522557394129080>",
	"fame-checker": "<:famechecker:1424522665833529385>",
	"tm-case": "<:tmcase:1424522749291925559>",
	"berry-pouch": "<:berrypouch:1424522888211337278>",
	"teachy-tv": "<:teachytv:1424523050912846006>",
	"powder-jar": "<:powderjar:1424507562778165290>",
	"pokeblock-case": "<:pokeblockcase:1424525322761666690>",
	"go-goggles": "<:gogoggles:1424525539112259647>",
	"devon-scope": "<:devonscope:1424563452449390653>",

	# Held Items
	"leftovers": "<:leftovers:1424483342992277709>",
	"bright-powder": "<:brightpowder:1424485395776929842>",
	"white-herb": "<:whiteherb:1424485572671705249>",
	"macho-brace": "<:machobrace:1424486175510364211>",
	"exp-share": "<:expshare:1424486248348647545>",
	"quick-claw": "<:quickclaw:1424486346185113670>",
	"soothe-bell": "<:soothebell:1424486466687336539>",
	"mental-herb": "<:mentalherb:1424486804115034253>",
	"choice-band": "<:choiceband:1424486907168948356>",
	"silver-powder": "<:silverpowder:1424487107132526602>",
	"amulet-coin": "<:amuletcoin:1424487187692523520>",
	"cleanse-tag": "<:cleansetag:1424487289605722162>",
	"soul-dew": "<:souldew:1424487377602089023>",
	"smoke-ball": "<:smokeball:1424487441703764220>",
	"everstone": "<:everstone:1424487751780139178>",
	"focus-band": "<:focusband:1424487808533397694>",
	"lucky-egg": "<:luckyegg:1424487893933621348>",
	"scope-lens": "<:scopelens:1424487968692895834>",
	"light-ball": "<:lightball:1424488023885873193>",
	"soft-sand": "<:softsand:1424488281311023104>",
	"hard-stone": "<:hardstone:1424488346704412726>",
	"miracle-seed": "<:miracleseed:1424488417315651766>",
	"black-glasses": "<:blackglasses:1424488500014747700>",
	"black-belt": "<:blackbelt:1424488579026911365>",
	"magnet": "<:magnet:1424488657540092065>",
	"mystic-water": "<:mysticwater:1424488731372425276>",
	"sharp-beak": "<:sharpbeak:1424488819108872367>",
	"poison-barb": "<:poisonbarb:1424489116174778459>",
	"never-melt-ice": "<:nevermeltice:1424489429417853038>",
	"spell-tag": "<:spelltag:1424489507667054612>",
	"twisted-spoon": "<:twistedspoon:1424489609269870748>",
	"charcoal": "<:charcoal:1424489768783319171>",
	"dragon-fang": "<:dragonfang:1424489854833524920>",
	"red-scarf": "<:redscarf:1424510705956159641>",
	"blue-scarf": "<:bluescarf:1424510790047895563>",
	"pink-scarf": "<:pinkscarf:1424510856984530944>",
	"yellow-scarf": "<:yellowscarf:1424510999100391454>",
	"silk-scarf": "<:silkscarf:1424490186481471620>",
	"shell-bell": "<:shellbell:1424490240449581108>",
	"sea-incense": "<:seaincense:1424490328521572352>",
	"lax-incense": "<:laxincense:1424501271431221361>",
	"thick-club": "<:thickclub:1424504329569833041>",
	"stick": "<:stick:1424504406459547728>",
	"metal-powder": "<:metalpowder:1424505607888699523>",
	"quick-powder": "<:quickpowder:1424505780065009777>",
	"lucky-punch": "<:luckypunch:1424505841502912563>",

	# Evolution Held Items
	"metal-coat": "<:metalcoat:1424467524216426617>",
	"dragon-scale": "<:dragonscale:1424467710238134285>",
	"up-grade": "<:upgrade:1424468242335924275>",
	"kings-rock": "<:kingsrock:1424468393653829774>",
	"deep-sea-tooth": "<:deepseatooth:1424468596507021432>",
	"deep-sea-scale": "<:deepseascale:1424468757132214306>",

	# Mail Items
	"orange-mail": "<:orangemail:1424505978958778459>",
	"harbor-mail": "<:harbormail:1424506026451013695>",
	"glitter-mail": "<:glittermail:1424506073624088668>",
	"mech-mail": "<:mechmail:1424506139336380429>",
	"wood-mail": "<:woodmail:1424506200485134461>",
	"wave-mail": "<:wavemail:1424506307926429780>",
	"bead-mail": "<:beadmail:1424506361693081660>",
	"shadow-mail": "<:shadowmail:1424506413010653387>",
	"tropic-mail": "<:tropicmail:1424506484334788748>",
	"dream-mail": "<:dreammail:1424506539338764352>",
	"fab-mail": "<:fabmail:1424506592002441216>",
	"retro-mail": "<:retromail:1424506642577358849>",

	# Fossils
	"helix-fossil": "<:helixfossil:1424506754250838056>",
	"dome-fossil": "<:domefossil:1424506820654792836>",
	"old-amber": "<:oldamber:1424506884118937631>",
	"root-fossil": "<:rootfossil:1424506933456535643>",
	"claw-fossil": "<:clawfossil:1424506980625551370>",

	# Mulch
	"growth-mulch": "<:growthmulch:1424507143893028915>",
	"damp-mulch": "<:dampmulch:1424507256225009684>",
	"stable-mulch": "<:stablemulch:1424507315947569223>",
	"gooey-mulch": "<:gooeymulch:1424507363372830863>",

	# Valuable Items (Sell Only)
	"nugget": "<:nugget:1424469160208891944>",
	"tiny-mushroom": "<:tinymushroom:1424469308225880084>",
	"big-mushroom": "<:bigmushroom:1424469458793136138>",
	"pearl": "<:pearl:1424469593937809518>",
	"big-pearl": "<:bigpearl:1424469737605435442>",
	"stardust": "<:stardust:1424469922901135422>",
	"star-piece": "<:starpiece:1424470073887822005>",
	"heart-scale": "<:heartscale:1424470245459886170>",
	"red-shard": "<:redshard:1424470428918743163>",
	"blue-shard": "<:blueshard:1424470589351006459>",
	"yellow-shard": "<:yellowshard:1424470769307615322>",
	"green-shard": "<:greenshard:1424470920436645930>",

	# Misc Items
	"shoal-salt": "<:shoalsalt:1424477398409154702>",
	"shoal-shell": "<:shoalshell:1424477401475448994>",
	"sacred-ash": "<:sacredash:1424477405371699242>",
	"balm-mushroom": "<:balmmushroom:1424477408655835262>",

	# Berries
	"cheri-berry": "<:cheriberry:1424492017458614353>",
	"chesto-berry": "<:chestoberry:1424492095812538408>",
	"pecha-berry": "<:pechaberry:1424492172945653830>",
	"rawst-berry": "<:rawstberry:1424492229938123005>",
	"aspear-berry": "<:aspearberry:1424492283528740916>",
	"leppa-berry": "<:leppaberry:1424492343750295602>",
	"oran-berry": "<:oranberry:1424492530195628102>",
	"persim-berry": "<:persimberry:1424492589297696833>",
	"lum-berry": "<:lumberry:1424492659870928896>",
	"sitrus-berry": "<:sitrusberry:1424492785980936285>",
	"figy-berry": "<:figyberry:1424492847188541695>",
	"wiki-berry": "<:wikiberry:1424492932408279386>",
	"mago-berry": "<:magoberry:1424493006303662280>",
	"aguav-berry": "<:aguavberry:1424493072552562718>",
	"iapapa-berry": "<:iapapaberry:1424493142027014365>",
	"razz-berry": "<:razzberry:1424493755737571499>",
	"bluk-berry": "<:blukberry:1424494419653955595>",
	"nanab-berry": "<:nanabberry:1424494469809569824>",
	"wepear-berry": "<:wepearberry:1424494520246079644>",
	"pinap-berry": "<:pinapberry:1424494574310785096>",
	"pomeg-berry": "<:pomegberry:1424494626710229253>",
	"kelpsy-berry": "<:kelpsyberry:1424494683945701511>",
	"qualot-berry": "<:qualotberry:1424494740660813944>",
	"hondew-berry": "<:hondewberry:1424494795811848384>",
	"grepa-berry": "<:grepaberry:1424494851503951974>",
	"tamato-berry": "<:tamatoberry:1424494914258862202>",
	"cornn-berry": "<:cornnberry:1424494971435880589>",
	"magost-berry": "<:magostberry:1424495035419983985>",
	"rabuta-berry": "<:rabutaberry:1424495089778163783>",
	"nomel-berry": "<:nomelberry:1424495168668831765>",
	"spelon-berry": "<:spelonberry:1424495216391360513>",
	"pamtre-berry": "<:pamtreberry:1424495540632289326>",
	"watmel-berry": "<:watmelberry:1424495603143934026>",
	"durin-berry": "<:durinberry:1424495658433515652>",
	"belue-berry": "<:belueberry:1424495711621222522>",
	"liechi-berry": "<:liechiberry:1424500799832195074>",
	"ganlon-berry": "<:ganlonberry:1424500886935437392>",
	"salac-berry": "<:salacberry:1424500936818298920>",
	"petaya-berry": "<:petayaberry:1424500986847822064>",
	"apicot-berry": "<:apicotberry:1424501038773309462>",
	"lansat-berry": "<:lansatberry:1424501080393252938>",
	"starf-berry": "<:starfberry:1424501126484590744>",
	"enigma-berry": "<:enigmaberry:1424501176849928204>",

	# HMs
	"hm01": "<:hm01:1424508131207020678>",
	"hm02": "<:hm02:1424508139876913232>",
	"hm03": "<:hm03:1424508273414897736>",
	"hm04": "<:hm04:1424508284559425649>",
	"hm05": "<:hm05:1424508294583549972>",
	"hm06": "<:hm06:1424508305341939802>",
	"hm07": "<:hm07:1424508313076236372>",
	"hm08": "<:hmnormal:1424514163043991645>",

	# TMs
	"tm01": "<:tmfighting:1424516719858155592>",
	"tm02": "<:tmdragon:1424516638979395705>",
	"tm03": "<:tmwater:1424517104450670765>",
	"tm04": "<:tmpsychic:1424517045583609876>",
	"tm05": "<:tmnormal:1424514276147728395>",
	"tm06": "<:tmpoison:1424516986108383384>",
	"tm07": "<:tmice:1424516913886920705>",
	"tm08": "<:tmfighting:1424516719858155592>",
	"tm09": "<:tmgrass:1424516868726718646>",
	"tm10": "<:tmnormal:1424514276147728395>",
	"tm11": "<:tmfire:1424516746383196182>",
	"tm12": "<:tmdark:1424516560327938130>",
	"tm13": "<:tmice:1424516913886920705>",
	"tm14": "<:tmice:1424516913886920705>",
	"tm15": "<:tmnormal:1424514276147728395>",
	"tm16": "<:tmpsychic:1424517045583609876>",
	"tm17": "<:tmnormal:1424514276147728395>",
	"tm18": "<:tmwater:1424517104450670765>",
	"tm19": "<:tmgrass:1424516868726718646>",
	"tm20": "<:tmnormal:1424514276147728395>",
	"tm21": "<:tmnormal:1424514276147728395>",
	"tm22": "<:tmgrass:1424516868726718646>",
	"tm23": "<:tmsteel:1424517093453332520>",
	"tm24": "<:tmelectric:1424516666393628672>",
	"tm25": "<:tmelectric:1424516666393628672>",
	"tm26": "<:tmelectric:1424516666393628672>",
	"tm27": "<:tmnormal:1424514276147728395>",
	"tm28": "<:tmelectric:1424516666393628672>",
	"tm29": "<:tmpsychic:1424517045583609876>",
	"tm30": "<:tmghost:1424516847226847343>",
	"tm31": "<:tmfighting:1424516719858155592>",
	"tm32": "<:tmnormal:1424514276147728395>",
	"tm33": "<:tmpsychic:1424517045583609876>",
	"tm34": "<:tmelectric:1424516666393628672>",
	"tm35": "<:tmelectric:1424516666393628672>",
	"tm36": "<:tmpoison:1424516986108383384>",
	"tm37": "<:tmrock:1424517074981490828>",
	"tm38": "<:tmfire:1424516746383196182>",
	"tm39": "<:tmrock:1424517074981490828>",
	"tm40": "<:tmflying:1424516796081242194>",
	"tm41": "<:tmdark:1424516560327938130>",
	"tm42": "<:tmnormal:1424514276147728395>",
	"tm43": "<:tmnormal:1424514276147728395>",
	"tm44": "<:tmpsychic:1424517045583609876>",
	"tm45": "<:tmnormal:1424514276147728395>",
	"tm46": "<:tmdark:1424516560327938130>",
	"tm47": "<:tmdark:1424516560327938130>",
	"tm48": "<:tmpsychic:1424517045583609876>",
	"tm49": "<:tmdark:1424516560327938130>",
	"tm50": "<:tmfire:1424516746383196182>",
}