# WorldAnvil-to-MD
Parses a World Anvil world export into Markdown files, primarily for [Obsidian](https://obsidian.md/). The script also adds some metadata yaml to the files and downloads images which are formatted as Obsidian embeds.

I wanted to bring my World Anvil content over to Obsidian but it was going to take me quite a bit of time to move it all over, much less in an organized fashion. Hence, this nifty bit of code.

If you're reading this, we're probably of a like mind, so I'll shout out two things that have made my GM'ing life far easier:
- If you use FoundryVTT for D&D like I do go check out this awesome plugin by Praxxian that lets you import Obsidian files, images and all, into Foundry: https://github.com/Praxxian/lava-flow
- I also highly recommend [Jeremy](https://github.com/valentine195) and all of their great Obsidian plugins for your D&D needs.

# Usage

## Using the script

All configs have been moved to configs.yaml for easy alteration/use.
The key variables you need to edit are:
```
source_directory = 'World-Anvil-Export'
destination_directory = 'World-Anvil-Output'
obsidian_resource_folder = 'images'

attempt_bbcode = True
```

``source_directory`` should point at the local folder with your world anvil exports
``destination_directory`` is where you want the formatted files and folders to end up
``obsidian_resource_folder`` is where the images will be stored
``attempt_bbcode`` determines whether or not it will attempt to convert BBCode to Markdown... it works sometimes, and probably is better than not doing so, but it isn't perfect

Once these variables are set run the script with Python and it will print output when it is done. If using Windows, you may instead just use the run.bat file to easily run the script. 
Images in Obsidian seem to have issues if not in png format, so the new c2png.py script was added to easily convert all files to png format. It will not delete the non-png originals though, that is on the user to decide to do. The command to use the image converter script is:
```
python c2png.py -all /images
```
This assumes you are running the command from within the project folder root, with the venv activated. If not, or don't know how to do so, use the imgFIX.bat to automatically do it for you, as long as your configs are using the default directories. 

## Sample file structire

An example file structure to export your files could look like so:
```
-> WorldAnvil-to-MD/
---> images/
---> World-Anvil-Export/
---> World-Anvil-Output/
---> WA-Parser.py
```

## Modifying

If you have any specialized sections or content tags you need to extract, you can try and add them under ``content_tags_to_extract``. Same with specific yaml metadata you want to add, you can try and add an additional entry under ``yaml_data``. The format is looking for nested tags, so keep that in mind depending on how nested your tags are.

## Exporting directly into your vault
It is recommended that you export to a separate folder rather than directly into your Obsidian vault, then when done simply drag the output into the vault.

However if you would like to import directly into your vault, change the ``destination_directory`` to the desired location in your vault and the ``obsidian_resource_folder`` path to your Obsidian attachments folder. I recommend backing up your vault before doing it with this method, as things may be overwritten if filenames match. But if you're brave, go for it.

# Exporting from World Anvil

See World Anvil's instructions on this here: https://blog.worldanvil.com/worldanvil/dev-news/new-feature-world-exporting/

A quick rundown on how it's done:
1. In World Anvil go to your world configuration page and select "Open Tools & Advanced Actions"
2. Select the dropdown for "EXPORT WORLD" click "Export this World"
3. You're going to need an API key for this. You can make one here: https://www.worldanvil.com/api/auth/key
4. To finalize the export you need to provide your API key and an email address, specifically a Google one according to World Anvil (This looks to because they are sharing a drive version of the export with you, rather than emailing it directly to you)
5. You can leave "Include Worlds" blank to export everthing, or specify a world name, then click Start
6. Once it is completed you will be emailed your world export

<a href="https://www.buymeacoffee.com/nynir" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
