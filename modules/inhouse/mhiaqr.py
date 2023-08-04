
import qrcode
class MhiaQR:
    def __init__(self, version=5, box_size=4, border=3) -> None: 
        
        self.qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )

    def generate(self, fill_color, back_color, data=None):
        self.qr.add_data(data)
        return self.qr.make_image(fill_color=fill_color, back_color=back_color)
 