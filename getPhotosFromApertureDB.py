import sqlite3
import argparse
from pathlib import Path
from shutil import copy2

def parse_args():
    parser = argparse.ArgumentParser(
        description='Aperture photo extractor using SQLITE db.')
    parser.add_argument('--aperture', required=True,
                        metavar='/path/to/aperture/lib',
                        help='Path to a aperture photo library.')
    parser.add_argument('--output-folder', required=True,
                        metavar='/path/to/output/folder',
                        help='Folder to store extracted folders')
    parser.add_argument('--dry-run', required=False,
                        action='store_true', help="If set true, does not do anything, only prints what it would do.")
    args = parser.parse_args()
    return args


def get_albums(sq_cur):
    sq_cur.execute("SELECT Z_PK, ZTITLE FROM ZGENERICALBUM WHERE ZTITLE IS NOT NULL")
    albums_raw = sq_cur.fetchall()

    return dict(albums_raw)


def get_assets(sq_cur):
    sq_cur.execute("SELECT Z_PK, ZDIRECTORY, ZFILENAME FROM ZGENERICASSET WHERE ZDIRECTORY IS NOT NULL AND ZFILENAME IS NOT NULL")
    assets_raw = sq_cur.fetchall()

    return {key : Path(direc)/Path(filename) for key, direc, filename in assets_raw}


def get_album_asset_link(sq_cur):
    sq_cur.execute("SELECT Z_34ASSETS, Z_26ALBUMS FROM Z_26ASSETS WHERE Z_34ASSETS IS NOT NULL AND Z_26ALBUMS IS NOT NULL")
    link_raw = sq_cur.fetchall()

    return dict(link_raw)


def append_photo(album, photo, album_photos_dict):
    if album not in album_photos_dict:
        album_photos_dict[album] = [photo]
    else:
        album_photos_dict[album].append(photo)


def export_photos(album_dict, asset_dict, asset_album_dict):
    album_photos_dict = {}
    for photo_id, photo_path in asset_dict.items():
        if photo_id not in asset_album_dict:
            append_photo("AAA_No_album", photo_path, album_photos_dict)
        else:
            key = album_dict[asset_album_dict[photo_id]]
            append_photo(key, photo_path, album_photos_dict)
    return album_photos_dict


def copy_photos(album_photos_dict, originals_path, output_path, dry_run):
    for album, photos in album_photos_dict.items():
        album_path = output_path / album
        album_path.mkdir(exist_ok=True)
        if not album_path.is_dir():
            print(f"Could not create folder {album_path}")
        else:
            for photo in photos:
                source = originals_path / photo
                if False: #not source.is_file():
                    print(f"Photo {source} does not exits.")
                else:
                    print(f"Copying {source} to {album_path}.")
                    if not dry_run:
                        copy2(source, album_path)


def main():
    args = parse_args()

    library_path = Path(args.aperture)
    output_path = Path(args.output_folder)

    if not library_path.is_dir():
        raise Exception(f"Incorrect path to library: {library_path}")

    db_path = library_path / "database" / "Photos.sqlite"

    if not db_path.is_file() or db_path.suffix != '.sqlite':
        raise Exception(f"Could not find database/Photos.sqlite in given path to library: {library_path}")

    originals_path = library_path / "originals"
    if not originals_path.is_dir():
        raise Exception(f"Could not find originals directory in given path to library: {library_path}")
    
    output_path.mkdir(exist_ok=True)
    if not output_path.is_dir():
        raise Exception(f"Invalid path output folder: {output_path}")

    photo_db = sqlite3.connect(str(db_path))

    album_dict = get_albums(photo_db.cursor())
    asset_dict = get_assets(photo_db.cursor())
    asset_album_dict = get_album_asset_link(photo_db.cursor())

    album_photos_dict = export_photos(album_dict, asset_dict, asset_album_dict)

    total_length = len(album_photos_dict)
    total_sum = 0
    for photos in album_photos_dict.values():
        total_sum+=len(photos)

    print(f"Number of albums: {total_length}")
    print(f"Number of photos: {total_sum}")

    copy_photos(album_photos_dict, originals_path, output_path, args.dry_run)


if __name__ == '__main__':
    main()