##########################################################################
# System/Library/Frameworks/CoreText.framework
##########################################################################
from ctypes import c_bool, c_double, c_uint32, c_void_p, cdll, util

from rubicon.objc.runtime import objc_const

######################################################################
core_text = cdll.LoadLibrary(util.find_library("CoreText"))
######################################################################

######################################################################
# CTFontManager.h

core_text.CTFontManagerRegisterFontsForURL.restype = c_bool
core_text.CTFontManagerRegisterFontsForURL.argtypes = [c_void_p, c_uint32, c_void_p]

######################################################################
# CTFont.h

core_text.CTFontCreateCopyWithAttributes.restype = c_void_p
core_text.CTFontCreateCopyWithAttributes.argtypes = [
    c_void_p,  # font (CTFontRef)
    c_double,  # size (CGFloat; 0 = keep current)
    c_void_p,  # matrix (CGAffineTransform*; NULL = identity)
    c_void_p,  # attributes (CTFontDescriptorRef)
]

######################################################################
# CTFontDescriptor.h

core_text.CTFontDescriptorCreateWithAttributes.restype = c_void_p
core_text.CTFontDescriptorCreateWithAttributes.argtypes = [c_void_p]

kCTFontVariationAttribute = objc_const(core_text, "kCTFontVariationAttribute")

######################################################################
# CTFontManagerScope.h

kCTFontManagerScopeNone = 0
kCTFontManagerScopeProcess = 1
kCTFontManagerScopePersistent = 2
kCTFontManagerScopeSession = 3
kCTFontManagerScopeUser = 2
