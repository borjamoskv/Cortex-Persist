#!/usr/bin/env python3
"""
Bandcamp Profile Mapper v3.0 — THROTTLED + WORKING
Uses curl (bypasses bot detection) + Bandcamp Mobile API.
Single-threaded with 2s delays to avoid rate limiting.

Expected runtime: ~25 min for 700 URLs
"""

import html as html_module
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

URLS = """https://basmooy.bandcamp.com
https://ansome.bandcamp.com
https://adrianalopez.bandcamp.com
https://abstractdivision.bandcamp.com
https://stanislav-tolkachev.bandcamp.com
https://uvb76music.bandcamp.com
https://sleeparchive.bandcamp.com
https://rebekahmusic.bandcamp.com
https://oscarmulero.bandcamp.com
https://exium.bandcamp.com
https://dvs1.bandcamp.com
https://endlec.bandcamp.com
https://charlton-music.bandcamp.com
https://lag-music.bandcamp.com
https://radial-music.bandcamp.com
https://paulbirken.bandcamp.com
https://shxcxchcxsh.bandcamp.com
https://echologist.bandcamp.com
https://perctrax.bandcamp.com
https://percmusic.bandcamp.com
https://ihatemodels.bandcamp.com
https://mannidee.bandcamp.com
https://daxj.bandcamp.com
https://scalameriya.bandcamp.com
https://truss-music.bandcamp.com
https://ghostinthemachine.bandcamp.com
https://clouds-music.bandcamp.com
https://aja-music.bandcamp.com
https://acerbic.bandcamp.com
https://and-music.bandcamp.com
https://keepsakes.bandcamp.com
https://lenskerecords.bandcamp.com
https://amelielens.bandcamp.com
https://farrago-music.bandcamp.com
https://airod.bandcamp.com
https://somarecords.bandcamp.com
https://slam-music.bandcamp.com
https://gary-beck.bandcamp.com
https://silicone-soul.bandcamp.com
https://envoy-music.bandcamp.com
https://alex-smoke.bandcamp.com
https://blueprintrecords.bandcamp.com
https://jamesruskin.bandcamp.com
https://surgeonmusic.bandcamp.com
https://regis-music.bandcamp.com
https://markbroom.bandcamp.com
https://oliverho.bandcamp.com
https://cari-lekebusch.bandcamp.com
https://lucysa.bandcamp.com
https://kangdingray.bandcamp.com
https://shifted.bandcamp.com
https://rrose.bandcamp.com
https://lakkermusic.bandcamp.com
https://xhinmusic.bandcamp.com
https://pfirter.bandcamp.com
https://caterinabarbieri.bandcamp.com
https://eomac.bandcamp.com
https://chevel.bandcamp.com
https://dadubmusic.bandcamp.com
https://oakemusic.bandcamp.com
https://abdullarashim.bandcamp.com
https://varg2tm.bandcamp.com
https://acronym-ne.bandcamp.com
https://dorisburg.bandcamp.com
https://ulwhednar.bandcamp.com
https://isorinne.bandcamp.com
https://korridor-music.bandcamp.com
https://evigt-morker.bandcamp.com
https://anthony-linell.bandcamp.com
https://aufnahmeundwiedergabe.bandcamp.com
https://ancient-methods.bandcamp.com
https://phase-fatale.bandcamp.com
https://sinoption.bandcamp.com
https://cold-cave.bandcamp.com
https://tokenrecords.bandcamp.com
https://kr-it.bandcamp.com
https://inigo-kennedy.bandcamp.com
https://jonas-kopp.bandcamp.com
https://sawlin.bandcamp.com
https://planetrhythm.bandcamp.com
https://reeko.bandcamp.com
https://eartoground.bandcamp.com
https://vinicius-honorio.bandcamp.com
https://clergyrecords.bandcamp.com
https://cleric-music.bandcamp.com
https://reflec-music.bandcamp.com
https://drumcode.bandcamp.com
https://adam-beyer.bandcamp.com
https://layton-giordani.bandcamp.com
https://bart-skils.bandcamp.com
https://enrico-sangiuliano.bandcamp.com
https://paula-temple.bandcamp.com
https://blawan.bandcamp.com
https://karenn.bandcamp.com
https://kobosil.bandcamp.com
https://headless-horseman.bandcamp.com
https://anetha.bandcamp.com
https://999999999.bandcamp.com
https://kmyle.bandcamp.com
https://valerie-ace.bandcamp.com
https://somniac-one.bandcamp.com
https://codex-empire.bandcamp.com
https://jk-flesh.bandcamp.com
https://orphx.bandcamp.com
https://verset-zero.bandcamp.com
https://operant-music.bandcamp.com
https://torn-relics.bandcamp.com
https://uncertain-music.bandcamp.com
https://dj-dextro.bandcamp.com
https://klint-music.bandcamp.com
https://chlar.bandcamp.com
https://offgrid-music.bandcamp.com
https://hertz-music.bandcamp.com
https://alarico.bandcamp.com
https://speed-j.bandcamp.com
https://speedy-j.bandcamp.com
https://ben-klock.bandcamp.com
https://marcel-dettmann.bandcamp.com
https://len-faki.bandcamp.com
https://ellen-allien.bandcamp.com
https://monolake.bandcamp.com
https://robert-henke.bandcamp.com
https://cryochamber.bandcamp.com
https://atrium-carceri.bandcamp.com
https://sphare-sechs.bandcamp.com
https://tineidae.bandcamp.com
https://lesa-listvy.bandcamp.com
https://northumbriamusic.bandcamp.com
https://mount-shrine.bandcamp.com
https://dahlias-tear.bandcamp.com
https://protoU.bandcamp.com
https://flowers-for-bodysnatchers.bandcamp.com
https://kammarheit.bandcamp.com
https://council-of-nine.bandcamp.com
https://aegri-somnia.bandcamp.com
https://shrine.bandcamp.com
https://a-cryo-chamber-collaboration.bandcamp.com
https://paleowolf.bandcamp.com
https://necronomicon.bandcamp.com
https://dronny-darko.bandcamp.com
https://wordclock.bandcamp.com
https://god-body-disconnect.bandcamp.com
https://halgrath.bandcamp.com
https://cities-last-broadcast.bandcamp.com
https://sjellos.bandcamp.com
https://apocryphos.bandcamp.com
https://megaptera.bandcamp.com
https://gydja.bandcamp.com
https://cold-meat-industry.bandcamp.com
https://lustmord.bandcamp.com
https://raison-detre.bandcamp.com
https://desiderii-marginis.bandcamp.com
https://deutsch-nepal.bandcamp.com
https://brighter-death-now.bandcamp.com
https://mz412.bandcamp.com
https://mortiis.bandcamp.com
https://arcana-music.bandcamp.com
https://ordo-rosarius-equilibrio.bandcamp.com
https://glacialmovements.bandcamp.com
https://netherworld-music.bandcamp.com
https://pjusk.bandcamp.com
https://loscil.bandcamp.com
https://new-risen-throne.bandcamp.com
https://cycliclaw.bandcamp.com
https://taphephobia.bandcamp.com
https://trepaneringsritualen.bandcamp.com
https://aural-hypnox.bandcamp.com
https://jarl-music.bandcamp.com
https://bohren-der-club-of-gore.bandcamp.com
https://rafael-anton-irisarri.bandcamp.com
https://william-basinski.bandcamp.com
https://thomas-koner.bandcamp.com
https://biosphere.bandcamp.com
https://tim-hecker.bandcamp.com
https://ben-frost.bandcamp.com
https://fennesz.bandcamp.com
https://kevin-drumm.bandcamp.com
https://phill-niblock.bandcamp.com
https://eliane-radigue.bandcamp.com
https://pauline-oliveros.bandcamp.com
https://sarah-davachi.bandcamp.com
https://kali-malone.bandcamp.com
https://ellen-arkbro.bandcamp.com
https://hospitalproductions.bandcamp.com
https://prurient.bandcamp.com
https://dominickfernow.bandcamp.com
https://vatican-shadow.bandcamp.com
https://lust-for-youth.bandcamp.com
https://pharmakon.bandcamp.com
https://the-body-band.bandcamp.com
https://lingua-ignota.bandcamp.com
https://author-and-punisher.bandcamp.com
https://whitehouse-music.bandcamp.com
https://consumer-electronics.bandcamp.com
https://cut-hands.bandcamp.com
https://ramleh.bandcamp.com
https://genocide-organ.bandcamp.com
https://skullflower.bandcamp.com
https://wolf-eyes.bandcamp.com
https://yellow-swans.bandcamp.com
https://the-haxan-cloak.bandcamp.com
https://gazelle-twin.bandcamp.com
https://blanck-mass.bandcamp.com
https://actress-music.bandcamp.com
https://arca-music.bandcamp.com
https://bok-bok.bandcamp.com
https://kelela.bandcamp.com
https://lotic-music.bandcamp.com
https://rabit-music.bandcamp.com
https://yves-tumor.bandcamp.com
https://eartheater.bandcamp.com
https://klein-music.bandcamp.com
https://hanson-records.bandcamp.com
https://tesco-organisation.bandcamp.com
https://freak-animal.bandcamp.com
https://no-rent-records.bandcamp.com
https://flennessy.bandcamp.com
https://yellow-green.bandcamp.com
https://misanthropic-agenda.bandcamp.com
https://malignant-records.bandcamp.com
https://warprecords.bandcamp.com
https://aphextwin.bandcamp.com
https://autechre.bandcamp.com
https://squarepusher.bandcamp.com
https://boards-of-canada.bandcamp.com
https://clark.bandcamp.com
https://flying-lotus.bandcamp.com
https://oneohtrix-point-never.bandcamp.com
https://bibio.bandcamp.com
https://battles-music.bandcamp.com
https://grizzly-bear.bandcamp.com
https://hudson-mohawke.bandcamp.com
https://plaid-music.bandcamp.com
https://sabres-of-paradise.bandcamp.com
https://broadcast-band.bandcamp.com
https://brian-eno.bandcamp.com
https://lapalux.bandcamp.com
https://darkstar-music.bandcamp.com
https://rustie.bandcamp.com
https://gaika.bandcamp.com
https://evian-christ.bandcamp.com
https://pan-label.bandcamp.com
https://lee-gamble.bandcamp.com
https://objekt-music.bandcamp.com
https://m-e-s-h.bandcamp.com
https://jlin.bandcamp.com
https://bill-kouligas.bandcamp.com
https://helm-music.bandcamp.com
https://yves-de-mey.bandcamp.com
https://inga-copeland.bandcamp.com
https://florian-hecker.bandcamp.com
https://raster-media.bandcamp.com
https://alva-noto.bandcamp.com
https://byetone.bandcamp.com
https://senking.bandcamp.com
https://frank-bretschneider.bandcamp.com
https://ninjatune.bandcamp.com
https://amon-tobin.bandcamp.com
https://bonobo-music.bandcamp.com
https://cinematic-orchestra.bandcamp.com
https://coldcut.bandcamp.com
https://dj-food.bandcamp.com
https://floating-points.bandcamp.com
https://jordan-rakei.bandcamp.com
https://kelis.bandcamp.com
https://the-bug.bandcamp.com
https://mr-scruff.bandcamp.com
https://roots-manuva.bandcamp.com
https://wiley.bandcamp.com
https://young-fathers.bandcamp.com
https://bicep.bandcamp.com
https://four-tet.bandcamp.com
https://caribou-music.bandcamp.com
https://daphni.bandcamp.com
https://jon-hopkins.bandcamp.com
https://nils-frahm.bandcamp.com
https://olafur-arnalds.bandcamp.com
https://brainfeeder.bandcamp.com
https://thundercat.bandcamp.com
https://kamasi-washington.bandcamp.com
https://taylor-mcferrin.bandcamp.com
https://teebs.bandcamp.com
https://jeremiah-jae.bandcamp.com
https://ghostly.bandcamp.com
https://matthew-dear.bandcamp.com
https://tycho.bandcamp.com
https://shigeto.bandcamp.com
https://gold-panda.bandcamp.com
https://heathered-pearls.bandcamp.com
https://lusine.bandcamp.com
https://school-of-seven-bells.bandcamp.com
https://beacon-music.bandcamp.com
https://planet-mu.bandcamp.com
https://u-ziq.bandcamp.com
https://venetian-snares.bandcamp.com
https://luke-vibert.bandcamp.com
https://ital-tek.bandcamp.com
https://machinedrum.bandcamp.com
https://kuedo.bandcamp.com
https://starkey.bandcamp.com
https://foodman.bandcamp.com
https://dj-rashad.bandcamp.com
https://dj-spinn.bandcamp.com
https://traxman.bandcamp.com
https://hyperdub.bandcamp.com
https://kode9.bandcamp.com
https://burial.bandcamp.com
https://zomby.bandcamp.com
https://dvance.bandcamp.com
https://king-midas-sound.bandcamp.com
https://laurel-halo.bandcamp.com
https://jessy-lanza.bandcamp.com
https://fatima-al-qadiri.bandcamp.com
https://cooly-g.bandcamp.com
https://scratcha-dva.bandcamp.com
https://max-cooper.bandcamp.com
https://rival-consoles.bandcamp.com
https://nathan-fake.bandcamp.com
https://apparat.bandcamp.com
https://moderat.bandcamp.com
https://modeselektor.bandcamp.com
https://robag-wruhme.bandcamp.com
https://todd-terje.bandcamp.com
https://lindstrom.bandcamp.com
https://royksopp.bandcamp.com
https://the-field.bandcamp.com
https://gas-music.bandcamp.com
https://wolfgang-voigt.bandcamp.com
https://pole-music.bandcamp.com
https://jan-jelinek.bandcamp.com
https://vladislav-delay.bandcamp.com
https://errorsmith.bandcamp.com
https://mika-vainio.bandcamp.com
https://pan-sonic.bandcamp.com
https://russell-haswell.bandcamp.com
https://peter-rehberg.bandcamp.com
https://oren-ambarchi.bandcamp.com
https://sunn-o.bandcamp.com
https://earth-music.bandcamp.com
https://boris-band.bandcamp.com
https://nadja-music.bandcamp.com
https://jesu.bandcamp.com
https://godflesh.bandcamp.com
https://justin-broadrick.bandcamp.com
https://scorn.bandcamp.com
https://techno-animal.bandcamp.com
https://aphex-twin.bandcamp.com
https://richard-d-james.bandcamp.com
https://afx.bandcamp.com
https://polygon-window.bandcamp.com
https://caustic-window.bandcamp.com
https://user18081971.bandcamp.com
https://grant-wilson-claridge.bandcamp.com
https://universal-indicator.bandcamp.com
https://bogdan-raczynski.bandcamp.com
https://plug-music.bandcamp.com
https://wagon-christ.bandcamp.com
https://kerrier-district.bandcamp.com
https://leila-music.bandcamp.com
https://cylob.bandcamp.com
https://ovuca.bandcamp.com
https://aleksi-perala.bandcamp.com
https://the-tuss.bandcamp.com
https://steinvord.bandcamp.com
https://gabber-modus-operandi.bandcamp.com
https://machine-girl.bandcamp.com
https://sewerslvt.bandcamp.com
https://breakcore.bandcamp.com
https://igorrr.bandcamp.com
https://ruby-my-dear.bandcamp.com
https://bong-ra.bandcamp.com
https://enduser.bandcamp.com
https://drumcorps.bandcamp.com
https://rotator.bandcamp.com
https://thrasher-music.bandcamp.com
https://hellfish.bandcamp.com
https://producer-dj.bandcamp.com
https://akira-the-don.bandcamp.com
https://mick-gordon.bandcamp.com
https://doom-eternal.bandcamp.com
https://perturbator.bandcamp.com
https://carpenter-brut.bandcamp.com
https://dance-with-the-dead.bandcamp.com
https://gost-music.bandcamp.com
https://magic-sword.bandcamp.com
https://synthwave-retro.bandcamp.com
https://gunship-music.bandcamp.com
https://the-midnight.bandcamp.com
https://fm-84.bandcamp.com
https://timecop1983.bandcamp.com
https://mitch-murder.bandcamp.com
https://lazerhawk.bandcamp.com
https://kavinsky.bandcamp.com
https://college-music.bandcamp.com
https://electric-youth.bandcamp.com
https://desire-music.bandcamp.com
https://health-noise.bandcamp.com
https://youth-code.bandcamp.com
https://author-punisher.bandcamp.com
https://street-sects.bandcamp.com
https://3teeth.bandcamp.com
https://front-line-assembly.bandcamp.com
https://front-242.bandcamp.com
https://nitzer-ebb.bandcamp.com
https://leaether-strip.bandcamp.com
https://skinny-puppy.bandcamp.com
https://ohgr.bandcamp.com
https://download-band.bandcamp.com
https://kmfdm.bandcamp.com
https://nine-inch-nails.bandcamp.com
https://ministry.bandcamp.com
https://my-life-with-the-thrill-kill-kult.bandcamp.com
https://revolting-cocks.bandcamp.com
https://pigface.bandcamp.com
https://bile-band.bandcamp.com
https://marilyn-manson.bandcamp.com
https://rob-zombie.bandcamp.com
https://ostgutton.bandcamp.com
https://berghain.bandcamp.com
https://tresor-records.bandcamp.com
https://hardwax.bandcamp.com
https://semantica-records.bandcamp.com
https://figure.bandcamp.com
https://techno-bunker.bandcamp.com
https://r-s-records.bandcamp.com
https://rekids.bandcamp.com
https://radio-slave.bandcamp.com
https://10000-suns.bandcamp.com
https://klockworks.bandcamp.com
https://prologue.bandcamp.com
https://pole-records.bandcamp.com
https://delsin.bandcamp.com
https://clone.bandcamp.com
https://rush-hour.bandcamp.com
https://boomkat.bandcamp.com
https://kompakt.bandcamp.com
https://michael-mayer.bandcamp.com
https://superpitcher.bandcamp.com
https://sascha-funke.bandcamp.com
https://thomas-fehlmann.bandcamp.com
https://the-orb.bandcamp.com
https://mixmaster-morris.bandcamp.com
https://sun-electric.bandcamp.com
https://air-music.bandcamp.com
https://daft-punk.bandcamp.com
https://justice-music.bandcamp.com
https://ed-banger.bandcamp.com
https://busy-p.bandcamp.com
https://mr-oizo.bandcamp.com
https://sebastian-music.bandcamp.com
https://breakbot.bandcamp.com
https://gesaffelstein.bandcamp.com
https://brodinski.bandcamp.com
https://surgeon-uk.bandcamp.com
https://regis-birmingham.bandcamp.com
https://female-music.bandcamp.com
https://andsomne.bandcamp.com
https://tommy-four-seven.bandcamp.com
https://t47.bandcamp.com
https://truncate.bandcamp.com
https://audio-injection.bandcamp.com
https://developer-music.bandcamp.com
https://orphx-band.bandcamp.com
https://phase-music.bandcamp.com
https://joris-voorn.bandcamp.com
https://2000-and-one.bandcamp.com
https://patrice-baumel.bandcamp.com
https://dave-clarke.bandcamp.com
https://chris-liebing.bandcamp.com
https://drumcell.bandcamp.com
https://raiz.bandcamp.com
https://stanny-franssen.bandcamp.com
https://luke-slater.bandcamp.com
https://planetary-assault-systems.bandcamp.com
https://mote-evolver.bandcamp.com
https://seventh-plain.bandcamp.com
https://l-b-dub-corp.bandcamp.com
https://shed-music.bandcamp.com
https://head-high.bandcamp.com
https://wk7.bandcamp.com
https://answer-code-request.bandcamp.com
https://roman-flugel.bandcamp.com
https://ata-music.bandcamp.com
https://dj-koze.bandcamp.com
https://remix-music.bandcamp.com
https://move-d.bandcamp.com
https://dixon.bandcamp.com
https://ame-music.bandcamp.com
https://frank-wiedemann.bandcamp.com
https://kristian-beyer.bandcamp.com
https://innervisions.bandcamp.com
https://stimming.bandcamp.com
https://pantha-du-prince.bandcamp.com
https://axel-boman.bandcamp.com
https://studio-barnhus.bandcamp.com
https://pedrodollar.bandcamp.com
https://bella-boo.bandcamp.com
https://baba-stiltz.bandcamp.com
https://jay-daniel.bandcamp.com
https://kyle-hall.bandcamp.com
https://moodymann.bandcamp.com
https://theo-parrish.bandcamp.com
https://omar-s.bandcamp.com
https://delano-smith.bandcamp.com
https://terrence-parker.bandcamp.com
https://juan-atkins.bandcamp.com
https://model-500.bandcamp.com
https://cybotron.bandcamp.com
https://derrick-may.bandcamp.com
https://rhythim-is-rhythim.bandcamp.com
https://kevin-saunderson.bandcamp.com
https://inner-city.bandcamp.com
https://e-dancer.bandcamp.com
https://galaxy-2-galaxy.bandcamp.com
https://underground-resistance.bandcamp.com
https://los-hermanos.bandcamp.com
https://timeline.bandcamp.com
https://drexciya.bandcamp.com
https://dopplereffekt.bandcamp.com
https://arpanet.bandcamp.com
https://der-zyklus.bandcamp.com
https://james-stinson.bandcamp.com
https://rob-hood.bandcamp.com
https://floorplan.bandcamp.com
https://m-plant.bandcamp.com
https://robert-hood.bandcamp.com
https://jeff-mills.bandcamp.com
https://axis-records.bandcamp.com
https://purpose-maker.bandcamp.com
https://tomorrow-comes-the-harvest.bandcamp.com
https://the-wizard.bandcamp.com
https://gerald-mitchell.bandcamp.com
https://carl-craig.bandcamp.com
https://paperclip-people.bandcamp.com
https://kenny-larkin.bandcamp.com
https://stacey-pullen.bandcamp.com
https://alan-oldham.bandcamp.com
https://dj-minus.bandcamp.com
https://richie-hawtin.bandcamp.com
https://plastikman.bandcamp.com
https://fuse-music.bandcamp.com
https://circuit-breaker.bandcamp.com
https://speedy-jay.bandcamp.com
https://arca.bandcamp.com
https://lotic.bandcamp.com
https://rabit.bandcamp.com
https://elysia-crampton.bandcamp.com
https://chino-amobi.bandcamp.com
https://angel-marcloid.bandcamp.com
https://fire-toolz.bandcamp.com
https://giant-claw.bandcamp.com
https://oneohtrixpointnever.bandcamp.com
https://hype-williams.bandcamp.com
https://dean-blunt.bandcamp.com
https://james-ferraro.bandcamp.com
https://fatimaaaa.bandcamp.com
https://nicolaas-jaar.bandcamp.com
https://darkside-music.bandcamp.com
https://contra-la-puerta.bandcamp.com
https://space-is-only-noise.bandcamp.com
https://kara-lis-coverdale.bandcamp.com
https://yves-tumorrr.bandcamp.com
https://kelela-music.bandcamp.com
https://serpentwithfeet.bandcamp.com
https://mosses-sumney.bandcamp.com
https://perfume-genius.bandcamp.com
https://sophi-xeon.bandcamp.com
https://felicita-music.bandcamp.com
https://ag-cook.bandcamp.com
https://danny-l-harle.bandcamp.com
https://easyefun.bandcamp.com
https://namasendaa.bandcamp.com
https://pc-music.bandcamp.com
https://hannah-diamond.bandcamp.com
https://gfoty.bandcamp.com
https://spinee.bandcamp.com
https://lili.bandcamp.com
https://iglooghost.bandcamp.com
https://kai-whiston.bandcamp.com
https://danny-watts.bandcamp.com
https://jpegmafia.bandcamp.com
https://ho99o9.bandcamp.com
https://clipping-music.bandcamp.com
https://death-grips.bandcamp.com
https://show-me-the-body.bandcamp.com
https://full-of-hell.bandcamp.com
https://code-orange.bandcamp.com
https://knocked-loose.bandcamp.com
https://turnstile.bandcamp.com
https://kreator.bandcamp.com
https://sodom.bandcamp.com
https://destruction.bandcamp.com
https://voivod.bandcamp.com
https://celtic-frost.bandcamp.com
https://triptykon.bandcamp.com
https://tom-g-warrior.bandcamp.com
https://neurosis.bandcamp.com
https://amenra.bandcamp.com
https://cult-of-luna.bandcamp.com
https://isis-band.bandcamp.com
https://pelican-music.bandcamp.com
https://russian-circles.bandcamp.com
https://mono-japan.bandcamp.com
https://mogwai.bandcamp.com
https://explosions-in-the-sky.bandcamp.com
https://godspeed-you-black-emperor.bandcamp.com
https://a-silver-mt-zion.bandcamp.com
https://do-make-say-think.bandcamp.com
https://constellation-records.bandcamp.com
https://kranky-records.bandcamp.com
https://stars-of-the-lid.bandcamp.com
https://the-dead-texan.bandcamp.com
https://grouper.bandcamp.com
https://julianna-barwick.bandcamp.com
https://tamaryn.bandcamp.com
https://chelsea-wolfe.bandcamp.com
https://king-woman.bandcamp.com
https://thou-band.bandcamp.com
https://the-body-thebody.bandcamp.com
https://uniform-band.bandcamp.com
https://nrq.bandcamp.com
https://portrayal-of-guilt.bandcamp.com
https://primitive-man.bandcamp.com
https://indian-band.bandcamp.com
https://coffinworm.bandcamp.com
https://dragged-into-sunlight.bandcamp.com
https://anaal-nathrakh.bandcamp.com
https://gnaw-their-tongues.bandcamp.com
https://mories.bandcamp.com
https://cloak-of-altering.bandcamp.com
https://de-magia-veterum.bandcamp.com
https://aderlansen.bandcamp.com
https://sewer-goddess.bandcamp.com
https://theology.bandcamp.com
https://nyodene-d.bandcamp.com
https://column-of-heaven.bandcamp.com
https://the-endless-blockade.bandcamp.com
https://bastard-noise.bandcamp.com
https://man-is-the-bastard.bandcamp.com
https://crossed-out.bandcamp.com
https://infest-band.bandcamp.com
https://despise-you.bandcamp.com
https://hatred-surge.bandcamp.com
https://nails-band.bandcamp.com
https://xibalba.bandcamp.com
https://weekend-nachos.bandcamp.com
https://harm-done.bandcamp.com
https://black-breath.bandcamp.com
https://trap-them.bandcamp.com
https://converge.bandcamp.com
https://jacob-bannon.bandcamp.com
https://godcity-online.bandcamp.com
https://kepleruk.bandcamp.com
https://speedyj.bandcamp.com
https://lone.bandcamp.com
https://djsprinter.bandcamp.com
https://femtanyl.bandcamp.com
https://mechatronica.bandcamp.com
https://unknown-untitled.bandcamp.com
https://doo-solution.bandcamp.com
https://surfaceaccess.bandcamp.com
https://nousklaer.bandcamp.com
https://nonseries.bandcamp.com
https://anthonyrother.bandcamp.com
https://djrum.bandcamp.com
https://hodgebristol.bandcamp.com
https://chrisliebing.bandcamp.com
https://technorecords.bandcamp.com
https://posthuman.bandcamp.com
https://zodiakcommunerecords.bandcamp.com
https://molekul.bandcamp.com
https://carre-carre.bandcamp.com
https://christianloffler.bandcamp.com
https://meatkatie.bandcamp.com
https://mykingislight.bandcamp.com
https://jameswelsh.bandcamp.com
https://atjazz.bandcamp.com
https://mightyforce.bandcamp.com
https://waxassassin.bandcamp.com
https://oddysee.bandcamp.com
https://boisha.bandcamp.com
https://mindhelmet.bandcamp.com
https://mainphase.bandcamp.com
https://kolter.bandcamp.com
https://fort-romeau.bandcamp.com
https://sonicmayhem.bandcamp.com
https://zenonrecords.bandcamp.com
https://mutual-rytm.bandcamp.com
https://insectorama.bandcamp.com
https://intlanthem.bandcamp.com
https://calibre.bandcamp.com
https://pugilist.bandcamp.com
https://tiga.bandcamp.com
https://jkflesh.bandcamp.com
https://datassette.bandcamp.com
https://lamsi.bandcamp.com
https://mannequinrecords.bandcamp.com
https://blurredline.bandcamp.com
https://hayescollective.bandcamp.com
https://wajang.bandcamp.com
https://smilesessions.bandcamp.com
https://baileyibbs.bandcamp.com
https://kosh212.bandcamp.com
https://customizedculturerecordings.bandcamp.com"""


def get_unique_urls():
    urls = [u.strip() for u in URLS.strip().split("\n") if u.strip()]
    seen = set()
    unique = []
    for url in urls:
        normalized = url.lower().rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            unique.append(url.strip())
    return unique


def curl_get_html(url):
    """Fetch page via curl with proper Sec-Fetch headers."""
    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-w",
                "\n%{http_code}",
                "--max-time",
                "10",
                "-H",
                "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "-H",
                "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-H",
                "Accept-Language: en-US,en;q=0.5",
                "-H",
                "Sec-Fetch-Dest: document",
                "-H",
                "Sec-Fetch-Mode: navigate",
                "-H",
                "Sec-Fetch-Site: none",
                "--compressed",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        lines = result.stdout.rsplit("\n", 1)
        if len(lines) == 2:
            return int(lines[1].strip()), lines[0]
        return 0, result.stdout
    except Exception:
        return 0, ""


def curl_post_api(band_id):
    """Call Bandcamp mobile API for band details."""
    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "--max-time",
                "10",
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "-H",
                "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "-d",
                json.dumps({"band_id": band_id}),
                "https://bandcamp.com/api/mobile/24/band_details",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.stdout:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def extract_band_id(body):
    """Extract band_id from HTML body (handles &quot; encoding)."""
    # data-band="..." contains HTML-encoded JSON
    m = re.search(r'data-band="([^"]+)"', body)
    if m:
        decoded = html_module.unescape(m.group(1))
        try:
            data = json.loads(decoded)
            return data.get("id")
        except json.JSONDecodeError:
            pass
        # Fallback: regex the decoded string
        m2 = re.search(r'"id"\s*:\s*(\d+)', decoded)
        if m2:
            return int(m2.group(1))

    # Fallback patterns
    m = re.search(r"&quot;id&quot;:(\d+)", body)
    if m:
        return int(m.group(1))

    m = re.search(r'"band_id"\s*:\s*(\d+)', body)
    if m:
        return int(m.group(1))

    return None


def extract_emails(text):
    """Find email addresses in text."""
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, text)
    blacklist = [
        "sentry",
        "example.com",
        "bandcamp.com",
        "schema.org",
        "w3.org",
        "googleapis",
        "ingest.us",
        "noreply",
        "github.com",
        "wixpress",
        "cloudflare",
        "webpack",
    ]
    return list(set(e for e in emails if not any(b in e.lower() for b in blacklist)))


def process_url(url, idx, total):
    """Full pipeline for one URL."""
    slug = url.replace("https://", "").replace(".bandcamp.com", "").rstrip("/")
    result = {
        "url": url,
        "slug": slug,
        "name": None,
        "band_id": None,
        "location": None,
        "bio": None,
        "sites": [],
        "emails": [],
        "status": "unknown",
        "is_label": False,
        "discography_count": 0,
    }

    # Phase 1: Get HTML page + extract band_id
    status_code, body = curl_get_html(url)

    if status_code == 404 or "doesn't exist" in body:
        result["status"] = "not_found"
        print(f"  [{idx}/{total}] ❌ {slug} — not found")
        return result

    if status_code != 200:
        result["status"] = f"http_{status_code}"
        print(f"  [{idx}/{total}] ⚠️ {slug} — HTTP {status_code}")
        return result

    band_id = extract_band_id(body)
    if not band_id:
        result["status"] = "no_band_id"
        print(f"  [{idx}/{total}] 🔍 {slug} — no band_id found")
        return result

    result["band_id"] = band_id

    # Brief pause before API call
    time.sleep(0.5)

    # Phase 2: Call mobile API
    details = curl_post_api(band_id)
    if not details:
        result["status"] = "api_error"
        print(f"  [{idx}/{total}] 🔌 {slug} — API error")
        return result

    result["status"] = "ok"
    result["name"] = details.get("name")
    result["location"] = details.get("location")
    result["bio"] = (details.get("bio") or "")[:500] or None

    # External links
    sites = details.get("sites", [])
    if sites:
        result["sites"] = [{"url": s.get("url", ""), "title": s.get("title", "")} for s in sites]

    # Artists = label
    if details.get("artists"):
        result["is_label"] = True

    # Discography
    result["discography_count"] = len(details.get("discography", []))

    # Detect labels from name
    name_lower = (result["name"] or "").lower()
    if any(kw in name_lower for kw in ["records", "recordings"]):
        result["is_label"] = True

    # Extract emails
    if result["bio"]:
        result["emails"].extend(extract_emails(result["bio"]))

    for site in result["sites"]:
        for field in [site.get("url", ""), site.get("title", "")]:
            if "mailto:" in field:
                email = field.replace("mailto:", "").split("?")[0].strip()
                if "@" in email:
                    result["emails"].append(email)
            result["emails"].extend(extract_emails(field))

    result["emails"] = list(set(result["emails"]))

    # Log
    loc = f" ({result['location']})" if result["location"] else ""
    sites_n = f" 🔗{len(result['sites'])}" if result["sites"] else ""
    email_str = f" 📧 {', '.join(result['emails'])}" if result["emails"] else ""
    label_str = " 🏷️" if result["is_label"] else ""
    print(f"  [{idx}/{total}] ✅ {result['name'] or slug}{loc}{label_str}{sites_n}{email_str}")

    return result


def generate_report(results, md_path):
    """Generate Markdown report."""
    ok = [r for r in results if r["status"] == "ok"]
    not_found = [r for r in results if r["status"] == "not_found"]
    errors = [r for r in results if r["status"] not in ("ok", "not_found")]
    with_emails = [r for r in ok if r["emails"]]
    with_sites = [r for r in ok if r["sites"]]

    lines = [
        "# 🎛️ Bandcamp Profile Map",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total scanned | {len(results)} |",
        f"| Active profiles | {len(ok)} |",
        f"| With emails | {len(with_emails)} |",
        f"| With ext links | {len(with_sites)} |",
        f"| Not found | {len(not_found)} |",
        f"| Errors | {len(errors)} |",
        "",
        "---",
        "",
    ]

    if with_emails:
        lines.append("## 📧 PROFILES WITH EMAIL")
        lines.append("")
        for i, r in enumerate(sorted(with_emails, key=lambda x: (x["name"] or "").lower()), 1):
            name = r["name"] or r["slug"]
            lines.append(f"### {i}. {name}")
            lines.append(f"- **Location:** {r['location'] or '—'}")
            lines.append(f"- **Bandcamp:** {r['url']}")
            for e in r["emails"]:
                lines.append(f"- **📧 Email:** `{e}`")
            for s in r["sites"]:
                lines.append(f"- **🔗** [{s['title']}]({s['url']})")
            if r["bio"]:
                lines.append(f"- **Bio:** {r['bio'][:200]}")
            lines.append("")
        lines.append("---\n")

    lines.append("## 🔗 ALL PROFILES WITH EXTERNAL LINKS")
    lines.append("")
    lines.append("| # | Name | Location | Links | Bandcamp |")
    lines.append("|---|------|----------|-------|----------|")
    for i, r in enumerate(sorted(with_sites, key=lambda x: (x["name"] or "").lower()), 1):
        name = r["name"] or r["slug"]
        loc = r["location"] or "—"
        link_list = ", ".join(f"[{s['title']}]({s['url']})" for s in r["sites"][:3])
        lines.append(f"| {i} | **{name}** | {loc} | {link_list} | [🔗]({r['url']}) |")
    lines.append("")

    lines.append("## 📋 ALL ACTIVE PROFILES")
    lines.append("")
    lines.append("| # | Name | Location | Releases | Bandcamp |")
    lines.append("|---|------|----------|----------|----------|")
    for i, r in enumerate(sorted(ok, key=lambda x: (x["name"] or "").lower()), 1):
        lines.append(
            f"| {i} | **{r['name'] or r['slug']}** | {r['location'] or '—'} | {r['discography_count']} | [🔗]({r['url']}) |"
        )
    lines.append("")

    if not_found:
        lines.append("## ❌ NOT FOUND\n")
        for r in sorted(not_found, key=lambda x: x["slug"]):
            lines.append(f"- `{r['slug']}`")
        lines.append("")

    if errors:
        lines.append("## ⚠️ ERRORS\n")
        for r in sorted(errors, key=lambda x: x["slug"]):
            lines.append(f"- `{r['slug']}` — {r['status']}")
        lines.append("")

    with open(md_path, "w") as f:
        f.write("\n".join(lines))


def main():
    urls = get_unique_urls()
    total = len(urls)

    print("\n🎛️  Bandcamp Profile Mapper v3.0")
    print(f"   {total} unique URLs — single thread, ~2s/req")
    print(f"   ETA: ~{total * 2.5 / 60:.0f} minutes\n")

    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    json_path = output_dir / "bandcamp_profiles.json"
    md_path = output_dir / "bandcamp_profiles.md"

    # Resume support: load existing results
    existing = {}
    if json_path.exists():
        try:
            with open(json_path) as f:
                prev = json.load(f)
            for r in prev:
                if r.get("status") == "ok":
                    existing[r["url"].lower().rstrip("/")] = r
            if existing:
                print(f"   💾 Resuming: {len(existing)} previously OK results loaded\n")
        except Exception:
            pass

    results = []
    for i, url in enumerate(urls, 1):
        url_key = url.lower().rstrip("/")
        if url_key in existing:
            results.append(existing[url_key])
            r = existing[url_key]
            email_str = f" 📧 {', '.join(r['emails'])}" if r.get("emails") else ""
            print(f"  [{i}/{total}] 💾 {r.get('name', r['slug'])} (cached){email_str}")
            continue

        result = process_url(url, i, total)
        results.append(result)

        # Save progress every 50 URLs
        if i % 50 == 0:
            with open(json_path, "w") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"  --- 💾 Progress saved ({i}/{total}) ---")

        # Throttle: 2s between page fetches
        time.sleep(2)

    # Final save
    results.sort(key=lambda x: x["slug"])
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    generate_report(results, md_path)

    ok_count = sum(1 for r in results if r["status"] == "ok")
    email_count = sum(1 for r in results if r.get("emails"))
    sites_count = sum(1 for r in results if r.get("sites"))

    print(f"\n{'=' * 50}")
    print(f"  ✅ Active: {ok_count}/{total}")
    print(f"  📧 With emails: {email_count}")
    print(f"  🔗 With ext links: {sites_count}")
    print(f"  💾 JSON: {json_path}")
    print(f"  📝 Report: {md_path}")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
